#include <windows.h>
#include <shlobj.h>
#include <stdio.h>
#include <string.h>

/* Ekrannik activation key (AE).
   1) deletes demo.flag next to Ekrannik.exe  -> full version
   2) writes license_AE.dat (marker)         -> stays activated even if
                                                 the demo installer is run again
   3) clears demo start date (file + registry)
   --silent -> no dialogs, exit code only (0 = ok, 2 = Ekrannik.exe not found)
*/

#define PRODUCT_CODE_STR "AE"
#define LICENSE_FILE L"license_AE.dat"
#define LICENSE_MARK L"f66e3325af59e2bcf8f06d84467009dc"

static int file_exists(const wchar_t *p) {
    DWORD a = GetFileAttributesW(p);
    return a != INVALID_FILE_ATTRIBUTES;
}

static void write_license(const wchar_t *dir) {
    wchar_t path[MAX_PATH * 2];
    _snwprintf(path, MAX_PATH * 2, L"%ls\\" LICENSE_FILE, dir);
    SetFileAttributesW(path, FILE_ATTRIBUTE_NORMAL);
    HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                           FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    const char *body = "Ekrannik AE\r\n"
                       "f66e3325af59e2bcf8f06d84467009dc\r\n"
                       "Activated. Do not delete this file.\r\n";
    DWORD w = 0;
    WriteFile(h, body, (DWORD)strlen(body), &w, NULL);
    CloseHandle(h);
    /* hide it, like other program service files */
    SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN);
}

static int try_unlock(const wchar_t *dir) {
    wchar_t exe[MAX_PATH * 2], flag[MAX_PATH * 2];
    _snwprintf(exe, MAX_PATH * 2, L"%ls\\Ekrannik.exe", dir);
    if (!file_exists(exe)) return 0;
    _snwprintf(flag, MAX_PATH * 2, L"%ls\\demo.flag", dir);
    if (file_exists(flag)) {
        SetFileAttributesW(flag, FILE_ATTRIBUTE_NORMAL);
        DeleteFileW(flag);
    }
    write_license(dir);
    return 1;
}

static void clear_date(void) {
    wchar_t appdata[MAX_PATH * 2], path[MAX_PATH * 2];
    if (SHGetFolderPathW(NULL, CSIDL_APPDATA, NULL, 0, appdata) == S_OK) {
        _snwprintf(path, MAX_PATH * 2, L"%ls\\MAMONOV\\.demo_date_" L"AE", appdata);
        if (file_exists(path)) {
            SetFileAttributesW(path, FILE_ATTRIBUTE_NORMAL);
            DeleteFileW(path);
        }
    }
    HKEY hk;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\MAMONOV", 0, KEY_SET_VALUE, &hk) == ERROR_SUCCESS) {
        RegDeleteValueW(hk, L"first_AE");
        RegCloseKey(hk);
    }
}

static void msg(const wchar_t *t) {
    MessageBoxW(NULL, t, L"Ekrannik", MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND);
}

static void self_delete(void) {
    wchar_t self[MAX_PATH * 2], cmd[MAX_PATH * 3];
    GetModuleFileNameW(NULL, self, MAX_PATH * 2);
    _snwprintf(cmd, MAX_PATH * 3,
               L"cmd.exe /c ping 127.0.0.1 -n 3 >nul & del /f /q \"%ls\"", self);
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    if (CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

int wmain(int argc, wchar_t **argv) {
    int silent = 0;
    for (int i = 1; i < argc; i++)
        if (wcscmp(argv[i], L"--silent") == 0) silent = 1;

    wchar_t local[MAX_PATH * 2] = {0}, pf[MAX_PATH * 2] = {0}, pf86[MAX_PATH * 2] = {0};
    SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, local);
    GetEnvironmentVariableW(L"ProgramFiles", pf, MAX_PATH * 2);
    GetEnvironmentVariableW(L"ProgramFiles(x86)", pf86, MAX_PATH * 2);

    wchar_t cand[5][MAX_PATH * 2];
    int n = 0;
    if (local[0]) { _snwprintf(cand[n], MAX_PATH * 2, L"%ls\\Programs\\Ekrannik", local); n++; }
    if (pf[0]) { _snwprintf(cand[n], MAX_PATH * 2, L"%ls\\Ekrannik", pf); n++; }
    if (pf86[0]) { _snwprintf(cand[n], MAX_PATH * 2, L"%ls\\Ekrannik", pf86); n++; }
    wchar_t self[MAX_PATH * 2];
    GetModuleFileNameW(NULL, self, MAX_PATH * 2);
    wchar_t *slash = wcsrchr(self, L'\\');
    if (slash) { *slash = 0; wcscpy(cand[n], self); n++; }

    int found = 0;
    for (int i = 0; i < n; i++) if (try_unlock(cand[i])) found = 1;

    if (!found) {
        if (!silent) msg(L"Ekrannik.exe \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.\n\n"
                         L"\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0443 \u0438 \u0437\u0430\u0442\u0435\u043c \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u043a\u043b\u044e\u0447.");
        return 2;
    }

    clear_date();

    if (!silent)
        msg(L"\u0413\u043e\u0442\u043e\u0432\u043e! \u0422\u0435\u043f\u0435\u0440\u044c \u0443 \u0432\u0430\u0441 \u043f\u043e\u043b\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f.\n\n"
            L"\u041e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u042d\u043a\u0440\u0430\u043d\u043d\u0438\u043a \u2014 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u0439 \u043f\u043e \u0434\u043d\u044f\u043c \u043d\u0435\u0442.");

    self_delete();
    return 0;
}
