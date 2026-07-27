#!/usr/bin/env bash
# Builds the Modbus/TCP parser (Week 1 - Packet Interceptor module)
set -e
g++ -std=c++17 -O2 -o modbus_parser src/modbus_parser.cpp
echo "Built ./modbus_parser"
