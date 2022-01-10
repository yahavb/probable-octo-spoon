import time
import signal 
import os
import datetime
import boto3
import random

cloudwatch = boto3.client('cloudwatch')

_sleeptime=int(os.environ['SLEEP_TIME'])

def sighandler(signum,frame):
  print('Signal handler was called with signal',signum)

def main():
  response = cloudwatch.put_metric_data(
    MetricData = [
        {
            'MetricName': 'NumOfJobs',
            'Dimensions': [
                {
                    'Name': 'MetricName',
                    'Value': 'NumOfJobsInvoked'
                },
                {
                    'Name': 'APP_VERSION',
                    'Value': 'x86-0.9'
                },
            ],
            'Unit': 'Count',
            'Value': 1
        },
    ],
    Namespace='pybusybox'
  )
  print("response="+str(response))
  while True:
    print('{0} pybusybox going to sleep for {1} sec'.format(datetime.datetime.now(),_sleeptime))
    time.sleep(_sleeptime)

if __name__ == '__main__':
  signal.signal(signal.SIGTERM,sighandler)
  print('signum {0} registered'.format(signal.SIGTERM))
  signal.signal(signal.SIGINT,sighandler)
  print('signum {0} registered'.format(signal.SIGINT))
  main()
