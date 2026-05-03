; cleansheet.iss  —  Inno Setup 6 installer script for CleanSheet v1.0.0
; Run: ISCC cleansheet.iss
; Output: installer\CleanSheet_Setup_v1.0.0.exe

#define AppName      "CleanSheet"
#define AppVersion   "1.0.0"
#define AppPublisher "Global Data 365"
#define AppExeName   "CleanSheet.exe"
#define AppURL       "https://globaldata365.com"
#define BuildDir     "dist\CleanSheet"

[Setup]
AppId={{A3F7C2B1-4E8D-4F2A-9C6B-1D5E8F3A7B2C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=no
LicenseFile=
; No license file required — license is enforced at runtime by the app itself
OutputDir=installer
OutputBaseFilename=CleanSheet_Setup_v{#AppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
; Preserve ProgramData on uninstall (user data / logs / config)
; Nothing in ProgramData is added to the [Files] section with uninstalldelete,
; and the [UninstallDelete] section deliberately omits that folder.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
; Create the ProgramData folder with Users-modify rights so the app can write
; app_config.json and logs without requiring elevation at runtime.
Name: "{commonappdata}\{#AppName}";        Permissions: users-modify
Name: "{commonappdata}\{#AppName}\logs";   Permissions: users-modify

[Files]
; All files from the PyInstaller one-dir build
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (optional, controlled by the Tasks section above)
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
; Register in Add/Remove Programs (Inno Setup does this automatically via AppId,
; but these keys make the entry richer in the Programs list)
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A3F7C2B1-4E8D-4F2A-9C6B-1D5E8F3A7B2C}_is1}"; \
    ValueType: string; ValueName: "DisplayName";    ValueData: "{#AppName} {#AppVersion}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A3F7C2B1-4E8D-4F2A-9C6B-1D5E8F3A7B2C}_is1}"; \
    ValueType: string; ValueName: "Publisher";      ValueData: "{#AppPublisher}"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A3F7C2B1-4E8D-4F2A-9C6B-1D5E8F3A7B2C}_is1}"; \
    ValueType: string; ValueName: "DisplayVersion";  ValueData: "{#AppVersion}"

[UninstallDelete]
; Remove the installation directory entirely on uninstall.
; C:\ProgramData\CleanSheet is intentionally NOT listed here —
; user data (logs, config, license) is preserved across uninstall/reinstall.
Type: filesandordirs; Name: "{app}"

[Run]
; Optionally launch the app after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
