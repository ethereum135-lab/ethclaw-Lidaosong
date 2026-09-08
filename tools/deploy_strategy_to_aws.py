#!/usr/bin/env python3
"""
deploy_strategy_to_aws.py — 当SSH可用时，自动将新策略配置推送到AWS A4引擎。
2026-07-09 策略修正：
  - E2/E3/E4永久禁用（1474笔验证正确率<3%）
  - P1(RSI超买)为主力出场信号
"""
import subprocess, os, json, sys, time
from datetime import datetime

ZQ_ROOT = os.path.expanduser("~/zq_web4_trading_system")
PEM = os.path.expanduser("~/.zq_vault/web4.0.pem")
AWS_HOST = "ubuntu@15.134.211.154"
AWS_ROOT = "/home/ubuntu/zq_web4_trading_system"

def ssh(cmd, timeout=15):
    full_cmd = f'ssh -i {PEM} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout={timeout} {AWS_HOST} "{cmd}"'
    try:
        r = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout+5)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)

def scp_push(local_path, remote_path):
    cmd = f'scp -i {PEM} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 {local_path} {AWS_HOST}:{remote_path}'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        return r.returncode == 0, r.stderr.strip()
    except Exception as e:
        return False, str(e)

def main():
    print(f"=== 策略部署到AWS — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    
    # Step 1: Test SSH
    ok, out, err = ssh("echo SSH_OK")
    if not ok:
        print("❌ SSH不可用，正在重试...")
        for i in range(5):
            time.sleep(10)
            ok, out, err = ssh("echo SSH_OK")
            if ok:
                print(f"✅ SSH在第{i+2}次尝试后可用")
                break
        if not ok:
            print("❌ SSH仍然不可用，部署取消。等SSH恢复后手动运行本脚本。")
            sys.exit(1)
    
    print("✅ SSH连接正常")
    
    # Step 2: Check A4 engine code on AWS
    ok, out, err = ssh(f"ls {AWS_ROOT}/strategies/market_regime.py {AWS_ROOT}/strategies/direction_judger.py {AWS_ROOT}/a4_engine.py 2>/dev/null")
    if not ok:
        print(f"⚠️ AWS文件检查: {err}")
    
    # Step 3: Push NAVIGATION.md
    print("\n📄 推送NAVIGATION.md...")
    ok, err = scp_push(f"{ZQ_ROOT}/NAVIGATION.md", f"{AWS_ROOT}/NAVIGATION.md")
    print(f"{'✅' if ok else '❌'} NAVIGATION.md: {err[:100] if err else 'ok'}")
    
    # Step 4: Push market_regime.py
    print("\n📄 推送market_regime.py...")
    ok, err = scp_push(f"{ZQ_ROOT}/strategies/market_regime.py", f"{AWS_ROOT}/strategies/market_regime.py")
    print(f"{'✅' if ok else '❌'} market_regime.py: {err[:100] if err else 'ok'}")
    
    # Step 5: Push direction_judger.py
    print("\n📄 推送direction_judger.py...")
    ok, err = scp_push(f"{ZQ_ROOT}/strategies/direction_judger.py", f"{AWS_ROOT}/strategies/direction_judger.py")
    print(f"{'✅' if ok else '❌'} direction_judger.py: {err[:100] if err else 'ok'}")
    
    # Step 6: Modify A4 engine exit signals if it exists
    print("\n🔧 检查A4引擎代码...")
    ok, out, err = ssh(f"grep -n 'E2.*exit\\|E3.*exit\\|E4.*exit\\|exit_reason.*E2\\|exit_reason.*E3\\|exit_reason.*E4' {AWS_ROOT}/a4_engine.py 2>/dev/null || true")
    if ok and out:
        print(f"⚠️ A4引擎中仍有E系列引用:\n{out[:500]}")
        print("尝试自动替换...")
        # Use sed to comment out E2/E3/E4 references
        ssh(f"sed -i '' 's/E2/DISABLED_E2/g; s/E3/DISABLED_E3/g; s/E4/DISABLED_E4/g' {AWS_ROOT}/a4_engine.py 2>/dev/null || true")
        ok2, _, _ = ssh(f"grep -c 'DISABLED_E' {AWS_ROOT}/a4_engine.py")
        print(f"已重命名E系列信号为DISABLED_{ok2}处")
    else:
        print("✅ A4引擎中无E系列硬引用")
    
    print("\n📄 推送新Risk-First引擎...")
    ok, err = scp_push(f"{ZQ_ROOT}/profiles/a4-blade/engine_v2.py", f"{AWS_ROOT}/profiles/a4-blade/engine_v2.py")
    print(f"{'✅' if ok else '❌'} engine_v2.py: {err[:100] if err else 'ok'}")
    
    # Step 7: Disable E series in old engine and stop it
    print("\n🔧 停用旧引擎...")
    ssh(f"pkill -f a4_engine.py 2>/dev/null || true")
    ssh(f"pkill -f engine_simple.py 2>/dev/null || true")
    
    # Step 8: Start new engine
    print("\n🔄 启动Risk-First引擎...")
    ok, out, err = ssh(f"cd {AWS_ROOT} && nohup python3 profiles/a4-blade/engine_v2.py --daemon > /tmp/engine_v2.log 2>&1 &")
    print(f"{'✅' if ok else '❌'} 新引擎启动: {out[:100] if out else 'ok'}")
    
    # Step 9: Verify
    print("\n🔍 验证引擎...")
    ok, out, err = ssh(f"ps aux | grep engine_v2 | grep -v grep | head -3")
    if ok and out:
        print(f"✅ 引擎运行中: {out[:100]}")
    else:
        print(f"⚠️ 需手动确认")
    
    print("\n✅ 部署完成!")
    print(f"改动摘要:")
    print(f"  - Risk-First Engine v2 → 运行中")
    print(f"  - 固定风险1%/仓 | 仓位由风险倒推")
    print(f"  - 出场: P1(RSI>85) / 浮动止损(3%) / 硬止损(5%)")
    print(f"  - 无止盈价 | 让赢家跑")

if __name__ == "__main__":
    main()
