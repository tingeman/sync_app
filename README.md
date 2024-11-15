# Sync App

This application is a system tray utility for scheduling and running synchronization jobs using FreeFileSync.

## Instructions for building into standalone app

1. **Install Python 3.6 or higher**: Ensure you have Python 3.6 or higher installed on your system.

2. **Install required packages**:

```
python -m pip install -r ./app/requirements.txt
```

3. **Build app**
```
pyinstaller --add-data "app/icons/*.ico:./icons/" --add-data "app/*.ini:." --hidden-import "pkg_resources" --noconsole ./app/sync_app.py
```

4. **Distribute app*: The application is accessible here: `./dist/sync_app/sync_app.exe`. All files and folders in the `./dist/sync_app` folder must be distributed with the executable.

## Running

1. **Install FreeFileSync**
2. **Create backup configuration**: Use FreeFileSync GUI interface to create a backup/synchronization setup, and save it.
3. **Update sync_app configuration**: 
   - Run the sync_app once by launching the `sync_app.exe` file.
   - Update the `config.ini` file with relevant paths and other settings
   - Quit the sync_app if still running (right-click icons in taskbar)
   - Relaunch the `sync_app.exe`
   - Optionally, use Windows Task Scheduler to launch `sync_app.exe` on start.
   - Optionally, ensure that the icons are constantly visible in the system tray notification area

## Configuration

```ini
[main]
sleepduration = 120

[SSD 1 Sync]
cmd = C:/Program Files/FreeFileSync/FreeFileSync.exe
args = C:/thin_private/Backup_profiles/SyncSettings_THIN_SSD_1.ffs_batch
every = 60
unit = minutes
LastRun = Never
LastDuration = None
LastResult = None
LastSuccess = Never

[WD 2 Sync]
cmd = C:/Program Files/FreeFileSync/FreeFileSync.exe
args = C:/thin_private/Backup_profiles/SyncSettings_THIN_SSD_2.ffs_batch
every = 60
unit = minutes
LastRun = Never
LastDuration = None
LastResult = None
LastSuccess = Never

```

First secion `[main]` is mandatory, and defines global options. `sleepduration` defines the interval in seconds with which the application wakes and executes any pending tasks.

Subsequent sections define the indivitual jobs. There can be one or multiple secionts/jobs. Each job
will get their own status icon in the task bar. 
`[section name]` is the name of the task.
`cmd` is the command to schedule (typically the launch of FreeFileSync)
`args` are the arguments to pass to `cmd`, typically the backup/sync configuration file
`every` is the interval at which the task is to be executed
`unit` is the unit of the interval specification ['seconds', 'minutes']

Remaining entries are status information written by the app itself.


    