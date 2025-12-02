; Inno Setup Script for MailConsolidator
; このスクリプトは MailConsolidator の Windows インストーラーを作成します

#define MyAppName "MailConsolidator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "techstrom"
#define MyAppURL "https://github.com/techstrom/MailConsolidator"
#define MyAppExeName "MailConsolidator.exe"

[Setup]
; アプリケーション基本情報
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; ライセンスファイル（オプション）
; LicenseFile=LICENSE
; 出力設定
OutputDir=installer_output
OutputBaseFilename=MailConsolidator-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 権限設定
PrivilegesRequired=lowest
; アイコン（オプション）
; SetupIconFile=icon.ico

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; PyInstaller でビルドした one-folder 形式のファイルをすべて含める
Source: "dist\MailConsolidator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; README などのドキュメント（オプション）
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; スタートメニューにショートカットを作成
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; デスクトップアイコン（タスクで選択された場合）
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; クイック起動アイコン（タスクで選択された場合）
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; インストール完了後にアプリケーションを起動するオプション
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; アンインストール時に設定ファイルを削除するかどうか（オプション）
; Type: filesandordirs; Name: "{userappdata}\MailConsolidator"
