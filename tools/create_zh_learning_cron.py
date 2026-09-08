#!/usr/bin/env python3
"""Create ZH-DeepLearning-15:00 cron job via the official Hermes cron API (A5 fix)."""
import sys, os

sys.path.insert(0, os.path.expanduser('~/.hermes/hermes-agent'))
os.chdir(os.path.expanduser('~/.hermes/hermes-agent'))

from cron.jobs import load_jobs, save_jobs, create_job

# Remove my earlier hand-written job if present (it lacks next_run_at)
jobs = load_jobs()
removed = [j for j in jobs if '深度学习' in j.get('name', '')]
jobs = [j for j in jobs if '深度学习' not in j.get('name', '')]
if removed:
    save_jobs(jobs)
    print('REMOVED hand-written:', [j['id'] for j in removed])

with open(os.path.expanduser('~/zq_web4_trading_system/tools/zh_learning_prompt.md')) as f:
    prompt = f.read()

job = create_job(
    schedule='0 15 * * *',
    prompt=prompt,
    name='ZH-深度学习-15:00',
    skills=['zh-commander-agent'],
    model='deepseek-v4-flash',
    provider='deepseek',
    workdir=os.path.expanduser('~/zq_web4_trading_system'),
    deliver='local',
)
print('CREATED:', job['name'], job['id'])
print('next_run_at:', job['next_run_at'])
print('created_at:', job['created_at'])
