#! C:\Users\thin\AppData\Local\Continuum\anaconda3\python.exe
# python v 3.6

# Need to install infi.systray like this:
# pip install infi.systray

# and schedule module using either conda or pip:
# conda install -c conda-forge schedule
# pip install schedule

# In order to make executable, install pyinstaller like this:
# > conda install -c conda-forge pyinstaller 
#
# Then run:
# > pyinstaller sync_app.py
#
# Then edit the generated *.spec file to include the following in the 'a' section:
#
# datas=[('./icons/*.ico', './icons/'),
#        ('./*.ini', '.')],
# hiddenimports=['pkg_resources'],
#
# and the follwing in the 'exe' section:
#
# console=False
#
# Now run:
# > pyinstaller sync_app.spec



from infi.systray import SysTrayIcon
import time
import schedule
import subprocess
import threading
import datetime as dt
import configparser
import json
import pathlib


#icons = glob.glob('./*.ico')
icons = {'error':   './icons/cancel.ico',
         'cancel':  './icons/cancel-1.ico',
         'success': './icons/checked-1.ico',
         'warning': './icons/information.ico',
         'working': './icons/cogwheel.ico',
         'idle':    './icons/clock.ico',
         'paused':  './icons/infinity.ico'}

ACTIVE_JOBS = {}
RUNNING_JOBS = {}
running_lock = threading.Lock()
config_lock = threading.Lock()

all_systrays = []

         
def write_status_file(systray):
    json_data = {'ACTIVE_JOBS': ACTIVE_JOBS,
                 'RUNNING_JOBS': RUNNING_JOBS,
                 '{0}_next_run'.format(all_systrays[0].name): str(all_systrays[0].job.next_run),
                 '{0}_next_run'.format(all_systrays[1].name): str(all_systrays[1].job.next_run),
                 'running_lock locked': running_lock.locked(),
                 'config_lock locked': config_lock.locked()
                 }
        
    pathlib.Path('./status').mkdir(parents=True, exist_ok=True) 
    with open('./status/sync_app_status_{0:%Y%m%d%H%M%S}.json'.format(dt.datetime.now()), 'w') as f:
        json.dump(json_data, f, ensure_ascii=False, sort_keys=True, indent=4)
        
    print('Status dumped to file...')
         


         
def on_quit_callback(systray):
    print('{0}: Now quiting...'.format(systray.name))
    schedule.clear(systray.name)
    ACTIVE_JOBS[systray.name] = False

def run_now(systray):
    print('{0}: Now running...'.format(systray.name))
    systray.job.job_func()
    
def pause(systray):    
    if systray.job in systray.job.scheduler.jobs:
        print('{0}: Now pausing...'.format(systray.name))
        systray.job.scheduler.jobs.remove(systray.job)
        systray_update(systray, icon=icons['paused'], status_str='PAUSED')
    else:
        print('{0}: Now resuming...'.format(systray.name))
        systray.job.scheduler.jobs.append(systray.job)
        systray_update(systray, icon=icons['idle'], status_str='Waiting...')
    
    
def run_job(systray, cmd, *args):
    if systray.name in RUNNING_JOBS and RUNNING_JOBS[systray.name]:
        return   # if job is already running, return (triggers rescheduling)
    
    RUNNING_JOBS[systray.name] = True
    job_thread = threading.Thread(target=execute_freefilesync, args=(systray, cmd, *args))
    job_thread.start()
    
    
def execute_freefilesync(systray, cmd, *args):
    global config
    
    with running_lock: # only run one sync process at a time
        print('{0}: Starting job...'.format(systray.name))
        RUNNING_JOBS[systray.name] = True
        run_started = dt.datetime.now()
        
        # Ensure that two calls/threads do not update properties at the same time
        with config_lock:   
            config[systray.name]['LastRun'] = '{0:%Y-%m-%d @ %H:%M}'.format(run_started)
            config[systray.name]['LastDuration'] = 'Still running...'
        write_config()
        
        systray_update(systray, icon=icons['working'], status_str='Working...')
        completed = subprocess.run(list((cmd, args)))
        run_duration = dt.datetime.now()-run_started

    # Ensure that two calls/threads do not update properties at the same time
    with config_lock:
        config[systray.name]['LastDuration'] = str(run_duration).split('.')[0]
        if completed.returncode == 0:
            config[systray.name]['LastResult'] = 'Success'
            config[systray.name]['LastSuccess'] = config[systray.name]['LastRun']
            systray_update(systray, icon=icons['success'], status_str='Waiting...')
        elif completed.returncode == 1:
            config[systray.name]['LastResult'] = 'Warnings'
            systray_update(systray, icon=icons['warning'], status_str='Waiting...')
        elif completed.returncode == 2:
            config[systray.name]['LastResult'] = 'Failed'
            systray_update(systray, icon=icons['error'], status_str='Waiting...')
        elif completed.returncode == 3:
            config[systray.name]['LastResult'] = 'Cancelled'
            systray_update(systray, icon=icons['cancel'], status_str='Waiting...')
        
    write_config()
    print('{0}: returncode: {1}'.format(systray.name, completed.returncode))
    RUNNING_JOBS[systray.name] = False
    
    """
    0 - Synchronization completed successfully
    1 - Synchronization completed with warnings
    2 - Synchronization completed with errors
    3 - Synchronization was aborted
    """



    
class MySysTrayIcon(SysTrayIcon):
    def __init__ (self, name, icon, hover_text, menu_options, **kwargs):
        menu_options = ((name, None, self.do_nothing),) + menu_options
        if hover_text is None:
            hover_text = ''
        super().__init__(icon, hover_text, menu_options, **kwargs)
        self.name = name
        ACTIVE_JOBS[name] = True
        self.job = None
        
    def do_nothing(self, systray):
        pass



def systray_update(systray, icon=None, status_str=None):
    global config
    hover_str = '{0}: {1}'.format(systray.name, status_str)
    if status_str == 'PAUSED':
        hover_str = hover_str + '\nNext run: Not scheduled'
    elif status_str == 'Working...':
        pass   # Don't add Next run information...
    else:
        if systray.job is not None:
            hover_str = hover_str + '\nNext run: {0:%Y-%m-%d @ %H:%M}'.format(systray.job.next_run)
        
    if config[systray.name]['LastRun'] != 'Never':
        if config[systray.name]['LastDuration'] == 'Still runnning...':
            hover_str = hover_str + '\nSuccess: {0}'.format(config[systray.name]['LastSuccess'])
        else:
            if config[systray.name]['LastResult'] == 'Success':
                hover_str = hover_str + '\nSuccess: {0}'.format(config[systray.name]['LastSuccess'])
            elif config[systray.name]['LastResult'] == 'Warnings':
                hover_str = hover_str + '\nWarnings: {0}'.format(config[systray.name]['LastRun'])
            elif config[systray.name]['LastResult'] == 'Failed':
                hover_str = hover_str + '\nFailed: {0}'.format(config[systray.name]['LastRun'])
                hover_str = hover_str + '\nSuccess: {0}'.format(config[systray.name]['LastSuccess'])
            elif config[systray.name]['LastResult'] == 'Cancelled':
                hover_str = hover_str + '\nCancelled: {0}'.format(config[systray.name]['LastRun'])
                hover_str = hover_str + '\nSuccess: {0}'.format(config[systray.name]['LastSuccess'])
            elif config[systray.name]['LastResult'] == 'Cancelled':
                hover_str = hover_str + '\nCancelled: {0}'.format(config[systray.name]['LastRun'])
                hover_str = hover_str + '\nSuccess: {0}'.format(config[systray.name]['LastSuccess'])
    
    systray.update(icon=icon, hover_text=hover_str)
    

def write_config():
    global config
    with config_lock:     # Ensure that two calls/threads do not write at the same time
        with open('config.ini', 'w') as configfile:
            config.write(configfile)        



def read_config():
    global config
    with config_lock:
        config = configparser.ConfigParser()
        config.optionxform=str   # In order to preserve case in config parameter names

        found_files = config.read('config.ini')

        if len(found_files) == 0:
            config['main'] =      {'sleepduration': '30'}
            config['WD 1 Sync'] = {'cmd':          'C:/Program Files/FreeFileSync/FreeFileSync.exe',
                                   'args':         'C:/thin_private/Backup_profiles/SyncSettings_THIN_WD_1.ffs_batch',
                                   'every':        '1',
                                   'unit':         'minutes',
                                   'LastRun':      'Never',
                                   'LastDuration': 'None',
                                   'LastResult':   'None',
                                   'LastSuccess':  'Never'}
            config['WD 2 Sync'] = {'cmd':          'C:/Program Files/FreeFileSync/FreeFileSync.exe',
                                   'args':         'C:/thin_private/Backup_profiles/SyncSettings_THIN_WD_2.ffs_batch',
                                   'every':        '1',
                                   'unit':         'minutes',
                                   'LastRun':      'Never',
                                   'LastDuration': 'None',
                                   'LastResult':   'None',
                                   'LastSuccess':  'Never'}
    write_config()
    return config

def register_jobs(config):
    menu_options = (('Run now', None, run_now),
                    ('Pause', None, pause),
                    ('Write status', None, write_status_file))        

    for section in config.sections():
        if section.lower() == 'main':
            continue
        name = section

        batch_file = config.get(section,'args').split()[0]
        if not pathlib.Path(batch_file).exists():
            # could not find batch file, so give an error message
            systray = MySysTrayIcon(name, icons['error'], '', (), on_quit=on_quit_callback)
            systray.start()
            all_systrays.append(systray)   # store in list, to always have access to them all
            systray_update(systray, icon=icons['error'], status_str='File not found: {0}'.format(batch_file))
            continue

        systray = MySysTrayIcon(name, icons['idle'], '', menu_options,
                                on_quit=on_quit_callback)
        systray.start()
        all_systrays.append(systray)   # store in list, to always have access to them all
        
        frequency = config.getint(section,'every')
        unit = config.get(section,'unit')
        if unit.lower() == 'minutes':
            job = schedule.every(frequency).minutes.do(run_job,       #execute_freefilesync, 
                                                       systray, 
                                                       config.get(section,'cmd'),
                                                       *config.get(section,'args').split()).tag(name)
        elif unit.lower() == 'seconds':
            job = schedule.every(frequency).seconds.do(run_job,       #execute_freefilesync, 
                                                       systray, 
                                                       config.get(section,'cmd'),
                                                       *config.get(section,'args').split()).tag(name)
        else:
            raise ValueError('Unit ''{0}'' not defined'.format(unit))
            
        systray.job = job
        systray_update(systray, icon=icons['idle'], status_str='Waiting...')
        
        print('Registered ''{0}'' to run every {1} {2}.'.format(name, frequency, unit))
        print('Next run scheduled at {0:%Y-%m-%d %H:%M}'.format(job.next_run))
    
def clear_all_jobs():
    global reconfiguring
    global config
    global ACTIVE_JOBS
    global RUNNING_JOBS
    
    for systray in all_systrays:
        print('{0}: Now quiting...'.format(systray.name))
        schedule.clear(systray.name)
        ACTIVE_JOBS[systray.name] = False
    
    ACTIVE_JOBS = {}
    RUNNING_JOBS = {}
    


config = read_config()
clear_all_jobs()
register_jobs(config)    
    
sleepduration = config.getint('main','sleepduration')
print('Infinite loop, checking schedule every {0} seconds.'.format(sleepduration))

while any(ACTIVE_JOBS.values() or reconfiguring):
    schedule.run_pending()
    time.sleep(sleepduration)
