#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>

#include <filesystem>
#include <string>
#include <vector>

namespace {

std::wstring quote_argument(const std::wstring& argument) {
    if (argument.find_first_of(L" \t\n\v\"") == std::wstring::npos)
        return argument;
    std::wstring quoted = L"\"";
    std::size_t backslashes = 0;
    for (const wchar_t character : argument) {
        if (character == L'\\') {
            ++backslashes;
            continue;
        }
        if (character == L'"') {
            quoted.append(backslashes * 2 + 1, L'\\');
            quoted.push_back(L'"');
            backslashes = 0;
            continue;
        }
        quoted.append(backslashes, L'\\');
        backslashes = 0;
        quoted.push_back(character);
    }
    quoted.append(backslashes * 2, L'\\');
    quoted.push_back(L'"');
    return quoted;
}

void append_argument(std::wstring& command, const std::wstring& argument) {
    if (!command.empty()) command.push_back(L' ');
    command += quote_argument(argument);
}

int show_error(const std::wstring& message) {
    MessageBoxW(
        nullptr, message.c_str(), L"SimAnt Macintosh Forged",
        MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
    return 2;
}

bool regular_file(const std::filesystem::path& path) {
    const DWORD attributes = GetFileAttributesW(path.c_str());
    return attributes != INVALID_FILE_ATTRIBUTES &&
           !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}

} // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    std::vector<wchar_t> module_buffer(32768);
    const DWORD module_length = GetModuleFileNameW(
        nullptr, module_buffer.data(),
        static_cast<DWORD>(module_buffer.size()));
    if (!module_length || module_length >= module_buffer.size())
        return show_error(L"Could not resolve the launcher location.");

    const std::filesystem::path application_dir =
        std::filesystem::path(
            std::wstring(module_buffer.data(), module_length)).parent_path();
    const std::filesystem::path runtime =
        application_dir / L"SimAntMacRuntime.exe";
    const std::filesystem::path original =
        application_dir / L"SimAnt_CD.iso";

    if (!regular_file(runtime))
        return show_error(
            L"SimAntMacRuntime.exe is missing. Extract every release file "
            L"into one directory.");
    if (!regular_file(original))
        return show_error(
            L"SimAnt_CD.iso was not found beside SimAntMac.exe. Copy your "
            L"lawful original Macintosh SimAnt CD image into this directory; "
            L"the original game is not included.");

    const std::filesystem::path artifact_dir = application_dir / L"artifacts";
    std::wstring command;
    append_argument(command, runtime.wstring());
    append_argument(command, original.wstring());
    append_argument(command, L"--creator");
    append_argument(command, L"SANT");
    append_argument(command, L"--expected-image-sha256");
    append_argument(
        command,
        L"8e7518796dbf32db9ff483dcc49069d4d8ec6e4625918fe4d47b03de8cc5fb0b");
    append_argument(command, L"--artifact-dir");
    append_argument(command, artifact_dir.wstring());

    int argument_count = 0;
    wchar_t** arguments = CommandLineToArgvW(
        GetCommandLineW(), &argument_count);
    if (arguments) {
        for (int index = 1; index < argument_count; ++index)
            append_argument(command, arguments[index]);
        LocalFree(arguments);
    }

    std::vector<wchar_t> mutable_command(command.begin(), command.end());
    mutable_command.push_back(L'\0');
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(
            runtime.c_str(), mutable_command.data(), nullptr, nullptr, FALSE,
            CREATE_UNICODE_ENVIRONMENT, nullptr, application_dir.c_str(),
            &startup, &process)) {
        return show_error(
            L"Could not start SimAntMacRuntime.exe (Windows error " +
            std::to_wstring(GetLastError()) + L").");
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}
