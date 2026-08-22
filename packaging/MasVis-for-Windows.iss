#ifndef MyAppVersion
  #define MyAppVersion "1.1.1"
#endif

#define MyAppName "MasVis for Windows"
#define MyAppExeName "MasVis-for-Windows.exe"
#define MyAppPublisher "adventureFAN"
#define MyAppURL "https://github.com/adventureFAN/MasVis-for-Windows"

[Setup]
AppId={{A33FD8B8-5598-4194-92EC-78FE8AB64C9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright=Copyright (C) 2026 adventureFAN
DefaultDirName={autopf}\MasVis for Windows
DefaultGroupName=MasVis for Windows
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupArchitecture=x64
OutputDir=..\release
OutputBaseFilename=MasVis-for-Windows-{#MyAppVersion}-Setup
SetupIconFile=..\assets\app\masvis-for-windows.ico
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
ChangesAssociations=no
ChangesEnvironment=no
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\MasVis-for-Windows\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MasVis for Windows"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\MasVis for Windows"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,MasVis for Windows}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
