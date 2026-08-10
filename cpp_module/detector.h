#ifndef DETECTOR_H
#define DETECTOR_H

#include <vector>
#include <string>

struct CompilerInfo {
    std::string name;       // Nombre amigable (ej. "GCC")
    std::string command;    // Comando ejecutable (ej. "gcc")
    std::string version;    // Versión detectada
    std::vector<std::string> extensions; // Extensiones asociadas
    std::string type;       // "compiler" o "interpreter"
};

std::vector<CompilerInfo> detect_compilers();

#endif