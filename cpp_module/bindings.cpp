#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "detector.h"

namespace py = pybind11;

PYBIND11_MODULE(cpp_module, m) {
    m.doc() = "Módulo C++ para detección de compiladores";
    
    py::class_<CompilerInfo>(m, "CompilerInfo")
        .def_readwrite("name", &CompilerInfo::name)
        .def_readwrite("command", &CompilerInfo::command)
        .def_readwrite("version", &CompilerInfo::version)
        .def_readwrite("extensions", &CompilerInfo::extensions)
        .def_readwrite("type", &CompilerInfo::type);
    
    m.def("detect_compilers", &detect_compilers, "Detecta compiladores instalados");
}