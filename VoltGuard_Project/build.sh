#!/usr/bin/env bash
# VoltGuard - Week 2 build script
# Builds the C++ Modbus parser, and (if Qt/qmake is available) the
# native dashboard foundation.

set -e

echo "== Building modbus_parser (C++) =="
if command -v g++ >/dev/null 2>&1; then
    g++ -std=c++17 -O2 -o modbus_parser src/modbus_parser.cpp
    echo "-> ./modbus_parser built."
else
    echo "g++ not found -- skipping parser build."
    echo "Install a C++ toolchain and re-run to build modbus_parser."
fi

echo ""
echo "== Building Qt dashboard (dashboard/) =="
if command -v qmake >/dev/null 2>&1; then
    ( cd dashboard && qmake && make )
    echo "-> dashboard/voltguard_dashboard built."
elif command -v qmake6 >/dev/null 2>&1; then
    ( cd dashboard && qmake6 && make )
    echo "-> dashboard/voltguard_dashboard built."
else
    echo "qmake not found -- skipping dashboard build."
    echo "Install Qt (qtbase5-dev / qt6-base-dev) and re-run to build the dashboard,"
    echo "or open dashboard/dashboard.pro in Qt Creator."
fi
