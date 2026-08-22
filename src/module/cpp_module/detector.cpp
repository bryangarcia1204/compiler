#include "detector.hpp"
#include <array>
#include <memory>
#include <string>
#include <vector>
#include <cstring>
#include <algorithm>
#include <filesystem>
#include <cstdlib>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

// Función para ejecutar un comando y capturar su salida (con timeout)
std::string exec(const char* cmd) {
#ifdef _WIN32
    HANDLE hReadPipe, hWritePipe;
    SECURITY_ATTRIBUTES sa = { sizeof(SECURITY_ATTRIBUTES), NULL, TRUE };
    if (!CreatePipe(&hReadPipe, &hWritePipe, &sa, 0))
        return "";

    PROCESS_INFORMATION pi;
    STARTUPINFOA si = { sizeof(STARTUPINFOA) };
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = hWritePipe;
    si.hStdError = hWritePipe;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);

    char* commandLine = new char[strlen(cmd) + 1];
    strcpy(commandLine, cmd);

    BOOL success = CreateProcessA(NULL, commandLine, NULL, NULL, TRUE,
                                   CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    if (!success) {
        delete[] commandLine;
        CloseHandle(hReadPipe);
        CloseHandle(hWritePipe);
        return "";
    }

    CloseHandle(hWritePipe);

    DWORD waitResult = WaitForSingleObject(pi.hProcess, 1000);
    if (waitResult != WAIT_OBJECT_0) {
        TerminateProcess(pi.hProcess, 1);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        delete[] commandLine;
        CloseHandle(hReadPipe);
        return "";
    }

    std::string result;
    char buffer[4096]; // Buffer más grande para mejor rendimiento
    DWORD bytesRead;
    while (ReadFile(hReadPipe, buffer, sizeof(buffer) - 1, &bytesRead, NULL) && bytesRead > 0) {
        buffer[bytesRead] = '\0';
        result += buffer;
    }

    CloseHandle(hReadPipe);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    delete[] commandLine;
    return result;
#else
    // En Unix: usar popen (con timeout simple)
    std::array<char, 4096> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);
    if (!pipe)
        return "";
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
#endif
}

// Función auxiliar para extraer la primera línea no vacía
std::string extract_first_line(const std::string& output) {
    size_t pos = output.find('\n');
    if (pos != std::string::npos) {
        std::string line = output.substr(0, pos);
        // Eliminar caracteres de retorno de carro (CR) si existen
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        return line;
    }
    return output;
}

bool command_exists(const std::string& cmd) {
#ifdef _WIN32
    std::string which_cmd = "where " + cmd + " > nul 2>&1";
#else
    std::string which_cmd = "command -v " + cmd + " > /dev/null 2>&1";
#endif
    return std::system(which_cmd.c_str()) == 0;
}

std::vector<CompilerInfo> detect_compilers() {
    std::vector<CompilerInfo> compilers;

    // --- GCC ---
    if (command_exists("gcc")){
    std::string gcc_version = exec("gcc --version");
    if (!gcc_version.empty()) {
        CompilerInfo info;
        info.name = "GCC";
        info.command = "gcc";
        info.version = extract_first_line(gcc_version);
        info.extensions = {".c"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    // --- G++ ---
    if (command_exists("g++")){
    std::string gpp_version = exec("g++ --version");
    if (!gpp_version.empty()) {
        CompilerInfo info;
        info.name = "G++";
        info.command = "g++";
        info.version = extract_first_line(gpp_version);
        info.extensions = {".cpp", ".cc", ".cxx"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    // --- Clang ---
    if (command_exists("g++")){
    std::string clang_version = exec("clang --version");
    if (!clang_version.empty()) {
        CompilerInfo info;
        info.name = "Clang";
        info.command = "clang";
        info.version = extract_first_line(clang_version);
        info.extensions = {".c", ".cpp", ".cc", ".cxx"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    // --- MSVC (solo en Windows) ---
#ifdef _WIN32
    if (command_exists("cl")){
    std::string msvc_version = exec("cl 2>&1");
    // Buscar la línea que contiene la versión (ej. "Microsoft (R) C/C++ Optimizing Compiler Version 19.xx.xxxxx for x86")
    if (!msvc_version.empty()) {
        size_t pos = msvc_version.find("Version");
        if (pos != std::string::npos) {
            size_t end = msvc_version.find('\n', pos);
            std::string version_line = msvc_version.substr(pos, end - pos);
            // Limpiar la línea
            version_line.erase(0, version_line.find_first_not_of(" \t\r\n"));
            version_line.erase(version_line.find_last_not_of(" \t\r\n") + 1);
            
            CompilerInfo info;
            info.name = "MSVC";
            info.command = "cl";
            info.version = version_line;
            info.extensions = {".c", ".cpp", ".cc", ".cxx"};
            info.type = "compiler";
            compilers.push_back(info);
            }
        }
    }
#endif

    // --- Zig ---
    if (command_exists("zig")){
    std::string zig_version = exec("zig version");
    if (!zig_version.empty()) {
        CompilerInfo info;
        info.name = "Zig";
        info.command = "zig";
        info.version = extract_first_line(zig_version);
        info.extensions = {".c", ".cpp", ".zig"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }
    // --- Python ---
    if (command_exists("python")){
    std::string python_version = exec("python --version");
    if (!python_version.empty()) {
        CompilerInfo info;
        info.name = "Python";
        info.command = "python";
        info.version = extract_first_line(python_version);
        info.extensions = {".py"};
        info.type = "interpreter";
        compilers.push_back(info);
        }
    }
    // --- Node.js ---
    if (command_exists("node")){
    std::string node_version = exec("node --version");
    if (!node_version.empty()) {
        CompilerInfo info;
        info.name = "Node.js";
        info.command = "node";
        info.version = extract_first_line(node_version);
        info.extensions = {".js"};
        info.type = "interpreter";
        compilers.push_back(info);
        }
    }

    // --- Java ---
    if (command_exists("javac")){
    std::string javac_version = exec("javac -version 2>&1");
    if (!javac_version.empty()) {
        CompilerInfo info;
        info.name = "Java";
        info.command = "javac";
        info.version = extract_first_line(javac_version);
        info.extensions = {".java"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    // --- Rust ---
    if (command_exists("rustc")){
    std::string rustc_version = exec("rustc --version");
    if (!rustc_version.empty()) {
        CompilerInfo info;
        info.name = "Rust";
        info.command = "cargo";
        info.version = extract_first_line(rustc_version);
        info.extensions = {".rs"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    // --- Go ---
    if (command_exists("go")){
    std::string go_version = exec("go version");
    if (!go_version.empty()) {
        CompilerInfo info;
        info.name = "Go";
        info.command = "go";
        info.version = extract_first_line(go_version);
        info.extensions = {".go"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    // --- Dotnet ---
    if (command_exists("dotnet")){
    std::string dotnet_version = exec("dotnet --version");
    if (!dotnet_version.empty()) {
        CompilerInfo info;
        info.name = "Dotnet";
        info.command = "dotnet";
        info.version = extract_first_line(dotnet_version);
        info.extensions = {".cs"};
        info.type = "compiler";
        compilers.push_back(info);
        }
    }

    return compilers;
}