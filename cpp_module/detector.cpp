#include "detector.h"
#include <cstdlib>
#include <cstdio>
#include <array>
#include <memory>
#include <sstream>
#include <algorithm>

#ifdef _WIN32
#include <windows.h>
#endif

std::string exec(const char* cmd) {
#ifdef _WIN32
    HANDLE hReadPipe, hWritePipe;
    SECURITY_ATTRIBUTES sa = { sizeof(SECURITY_ATTRIBUTES), NULL, TRUE };
    if (!CreatePipe(&hReadPipe, &hWritePipe, &sa, 0))
        return "";

    PROCESS_INFORMATION pi;
    STARTUPINFOA si = { sizeof(STARTUPINFOA) };
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;               // Ocultar ventana
    si.hStdOutput = hWritePipe;
    si.hStdError = hWritePipe;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);

    char* commandLine = new char[strlen(cmd) + 1];
    strcpy(commandLine, cmd);

    // Crear proceso sin ventana (CREATE_NO_WINDOW) y con ventana oculta
    BOOL success = CreateProcessA(NULL, commandLine, NULL, NULL, TRUE,
                                  CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    if (!success) {
        delete[] commandLine;
        CloseHandle(hReadPipe);
        CloseHandle(hWritePipe);
        return "";
    }

    // Cerrar el lado de escritura del pipe en el padre
    CloseHandle(hWritePipe);

    // Esperar con timeout corto (1 segundo)
    DWORD waitResult = WaitForSingleObject(pi.hProcess, 1000);
    if (waitResult != WAIT_OBJECT_0) {
        TerminateProcess(pi.hProcess, 1);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        delete[] commandLine;
        CloseHandle(hReadPipe);
        return "";
    }

    // Leer toda la salida del pipe
    std::string result;
    char buffer[128];
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
    // En Unix: usar popen (con timeout simple, pero se puede mejorar)
    std::array<char, 128> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);
    if (!pipe) return "";
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
#endif
}

// El resto de detect_compilers() se mantiene igual
std::vector<CompilerInfo> detect_compilers() {
    std::vector<CompilerInfo> compilers;
    
    // GCC
    std::string gcc_version = exec("gcc --version");
    if (!gcc_version.empty()) {
        CompilerInfo info;
        info.name = "GCC";
        info.command = "gcc";
        info.version = gcc_version.substr(0, gcc_version.find('\n'));
        info.extensions = {".c"};
        info.type = "compiler";
        compilers.push_back(info);
    }
    
    // G++
    std::string gpp_version = exec("g++ --version");
    if (!gpp_version.empty()) {
        CompilerInfo info;
        info.name = "G++";
        info.command = "g++";
        info.version = gpp_version.substr(0, gpp_version.find('\n'));
        info.extensions = {".cpp", ".cc", ".cxx"};
        info.type = "compiler";
        compilers.push_back(info);
    }
    
    // Clang
    std::string clang_version = exec("clang --version");
    if (!clang_version.empty()) {
        CompilerInfo info;
        info.name = "Clang";
        info.command = "clang";
        info.version = clang_version.substr(0, clang_version.find('\n'));
        info.extensions = {".c", ".cpp", ".cc", ".cxx"};
        info.type = "compiler";
        compilers.push_back(info);
    }
    
    // Python (intérprete)
    std::string python_version = exec("python --version");
    if (!python_version.empty()) {
        CompilerInfo info;
        info.name = "Python";
        info.command = "python";
        info.version = python_version.substr(0, python_version.find('\n'));
        info.extensions = {".py"};
        info.type = "interpreter";
        compilers.push_back(info);
    }
    
    // Node.js (intérprete)
    std::string node_version = exec("node --version");
    if (!node_version.empty()) {
        CompilerInfo info;
        info.name = "Node.js";
        info.command = "node";
        info.version = node_version.substr(0, node_version.find('\n'));
        info.extensions = {".js"};
        info.type = "interpreter";
        compilers.push_back(info);
    }
    
    // Java (compilador)
    std::string javac_version = exec("javac -version");
    if (!javac_version.empty()) {
        CompilerInfo info;
        info.name = "Java";
        info.command = "javac";
        info.version = javac_version.substr(0, javac_version.find('\n'));
        info.extensions = {".java"};
        info.type = "compiler";
        compilers.push_back(info);
    }
    
    // Rust
    std::string rustc_version = exec("rustc --version");
    if (!rustc_version.empty()) {
        CompilerInfo info;
        info.name = "Rust";
        info.command = "cargo";
        info.version = rustc_version.substr(0, rustc_version.find('\n'));
        info.extensions = {".rs"};
        info.type = "compiler";
        compilers.push_back(info);
    }

    // Go
    std::string go_version = exec("go version");
    if (!go_version.empty()) {
        CompilerInfo info;
        info.name = "Go";
        info.command = "go";
        info.version = go_version.substr(0, go_version.find('\n'));
        info.extensions = {".go"};
        info.type = "compiler";
        compilers.push_back(info);
    }

    // Dotnet
    std::string dotnet_version = exec("dotnet --version");
    if (!dotnet_version.empty()) {
        CompilerInfo info;
        info.name = "Dotnet";
        info.command = "dotnet";
        info.version = dotnet_version.substr(0, dotnet_version.find('\n'));
        info.extensions = {".cs"};
        info.type = "compiler";
        compilers.push_back(info);
    }
    
    return compilers;
}