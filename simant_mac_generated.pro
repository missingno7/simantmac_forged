QT += core gui widgets
CONFIG += c++17 console
CONFIG -= app_bundle
DEFINES += QT_NO_KEYWORDS
TEMPLATE = app
TARGET = pf_mac_qt_generated

DESTDIR = $$OUT_PWD
OBJECTS_DIR = $$OUT_PWD/obj
MOC_DIR = $$OUT_PWD/moc
RCC_DIR = $$OUT_PWD/rcc
UI_DIR = $$OUT_PWD/ui

INCLUDEPATH += $$PWD $$PWD/port_forge
SOURCES += $$PWD/native/simant_mac_qt.cpp

win32:LIBS += -lwinmm
win32-g++:QMAKE_LFLAGS += -Wl,--no-insert-timestamp
