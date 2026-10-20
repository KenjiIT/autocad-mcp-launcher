#ifndef AppVersion
  #define AppVersion "0.1.1"
#endif

#ifndef SourceRoot
  #define SourceRoot "..\dist\installer-payload\autocad-mcp-launcher"
#endif

[Setup]
AppId={{619FC921-6CF7-4A4E-B3FE-4BD564BCF300}
AppName=AutoCAD MCP Launcher
AppVersion={#AppVersion}
AppPublisher=KenjiIT
AppPublisherURL=https://github.com/KenjiIT/autocad-mcp-launcher
AppSupportURL=https://github.com/KenjiIT/autocad-mcp-launcher/issues
DefaultDirName={localappdata}\Programs\AutoCAD MCP Launcher
DefaultGroupName=AutoCAD MCP Launcher
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
UsePreviousAppDir=yes
UninstallDisplayName=AutoCAD MCP Launcher
UninstallDisplayIcon={app}\Start AutoCAD MCP.vbs
OutputDir=..\dist
OutputBaseFilename=AutoCAD-MCP-Launcher-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupLogging=yes

[Languages]
Name: "vietnamese"; MessagesFile: "Vietnamese.isl"

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut trên Desktop"; GroupDescription: "Shortcut bổ sung:"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AutoCAD MCP Launcher"; Filename: "{app}\Start AutoCAD MCP.vbs"; WorkingDir: "{app}"
Name: "{autodesktop}\AutoCAD MCP Launcher"; Filename: "{app}\Start AutoCAD MCP.vbs"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Start AutoCAD MCP.vbs"; Description: "Khởi chạy AutoCAD MCP Launcher"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent
