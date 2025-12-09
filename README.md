
# UMAT (Uma Musume Auto Train)
<a href="http://discord.gg/PhVmBtfsKp" target="_blank"><img src="https://img.shields.io/discord/1399387259245166674?color=5865F2&label=Join%20our%20Discord&logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord server"></a>

<a href="https://www.buymeacoffee.com/kisegami" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 30px !important;width: 180px !important;" ></a>
 

An automated training bot for Uma Musume: Pretty Derby that works with **Android emulators** using ADB (Android Debug Bridge). This aim for fully automate gameplay for busy players.
Right now **UMAT** support 2 senario: **URA Finales** and **Unity Cup**

## Highlighted Features
- **Easy to setup and config:** Using automated setup and really simple but efficient config for your training 
- **Score based training system:** Calculate score to train using elements like Support cards, hint, bond,...
- **Custom Race**: Do custom races as you setup for your run
- **Auto Skill Learning:** Auto learn necessary skills based on customizable config
- **Auto event choices picking:** Auto choose event option based on customize priority
- **Auto Update:** Auto update files and resources without needing to do it manually
## Getting Started

### Requirements

#### Software Requirements
- [Python 3.10+](https://www.python.org/downloads/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for text recognition)

#### Android Emulator Requirements
- **Supported Emulators**: The test was done on Mumu Emulator 12, but you might be able to use others
- **Emulator Resolution**: 1080x1920 (Portrait mode)
- **ADB Debugging**: Must be enabled in emulator settings

### Setup
#### 1. Download from [Releases](https://github.com/Kisegami/Uma-Musume-Emulator-Auto-Train/releases)
#### 2. Install Tesseract OCR

1. Download and install from [UB-Mannheim's Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add Tesseract to your system PATH

#### 4. Configure Android Emulator

1. **Install an Android emulator** (Mumu Emulator 12 or LDPlayer9 recommended)
2. **Set resolution to 1080x1920** (portrait mode)
3. **Enable ADB debugging** in emulator settings
4. **Install Uma Musume** in the emulator

#### 5. Install Python Dependencies

Run `install_dependencies.bat` from the UMAT folder to install all required Python packages.

Alternatively, you can manually install dependencies using:
```
toolkit\python\python.exe -m pip install -r requirements.txt
```

#### 6. Run Launch.bat to start the GUI

## Configs
Refer to [Config Guide](https://github.com/Kisegami/Uma-Musume-Emulator-Auto-Train/wiki/Config-Guide-%5BEN%5D)

### Contribute
If you run into any issues or something doesn't work as expected, feel free to open an issue.
Contributions are also very welcome, I would truly appreciate any support to help improve this project further.
