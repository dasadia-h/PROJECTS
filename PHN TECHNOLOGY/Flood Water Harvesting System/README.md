# Flood Water Harvesting & Recycling System

A prototype smart flood water harvesting system that tackles urban flooding by replacing narrow roadside drains with full-length road-border grills, channeling excess water through staged filtration before pumping it to residential overhead tanks.

Three buildings are modeled, each with an underground tank and an overhead tank. Dual float sensors per tank automate pumping, prevent overflow, and avoid running pumps dry unnecessarily.

## How It Works

| Condition | Action |
|-----------|--------|
| Underground tank has water + overhead tank needs a top-up | Pump turns ON |
| Underground tank is empty | Pump turns OFF |
| Overhead tank is full | Pump turns OFF |

The Serial Monitor logs each pump decision in real time.

## Hardware

- Arduino Uno
- Float sensors (2 per tank, 12 total across 3 buildings)
- Relay module (1 channel per building, 3 total)
- Submersible water pumps (1 per building)

## Pin Mapping

| Component | Pin |
|-----------|-----|
| Building 1 underground low sensor | D2 |
| Building 1 underground high sensor | D3 |
| Building 1 overhead low sensor | D4 |
| Building 1 overhead high sensor | D5 |
| Building 1 pump relay | D6 |
| Building 2 underground low sensor | D7 |
| Building 2 underground high sensor | D8 |
| Building 2 overhead low sensor | D9 |
| Building 2 overhead high sensor | D10 |
| Building 2 pump relay | D11 |
| Building 3 underground low sensor | D12 |
| Building 3 underground high sensor | D13 |
| Building 3 overhead low sensor | A0 |
| Building 3 overhead high sensor | A1 |
| Building 3 pump relay | A2 |

## Setup

1. Open `flood_water_system.ino` in the Arduino IDE
2. Upload to Arduino Uno
3. Open Serial Monitor at 9600 baud to watch pump decisions live

## Tech Stack
Arduino, Embedded C, Float Sensors, Relay Control, Automated Water Level Management
