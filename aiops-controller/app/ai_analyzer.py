import json
import logging
from typing import Any, Dict, Optional
import requests
from app.config import settings
from app.incident import AIAnalysisResult, Incident

logger = logging.getLogger("aiops_controller")


class NvidiaAIAnalyzer:
    """
    Isolated interface for analyzing incidents using NVIDIA AI NIM API with JSON schema enforcement.
    """
    def __init__(
        self,
        api_key: str = settings.NVIDIA_API_KEY,
        model: str = settings.NVIDIA_MODEL,
        base_url: str = settings.NVIDIA_BASE_URL,
        confidence_threshold: float = settings.AI_CONFIDENCE_THRESHOLD
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.confidence_threshold = confidence_threshold

    def analyze_incident(self, incident: Incident) -> Optional[AIAnalysisResult]:
        """
        Sends incident context to NVIDIA AI model and returns validated AIAnalysisResult.
        """
        prompt = self._build_prompt(incident)

        # Log the user prompt as a structured Kibana field (ai.prompt)
        logger.info(
            f"AI prompt built for incident {incident.crawler_id}:{incident.run_id}",
            extra={"ai_prompt": prompt}
        )

        # Demo mode / offline fallback when demo_key is used
        if self.api_key == "demo_key" or settings.AIOPS_DEMO_MODE:
            logger.info("AIOPS_DEMO_MODE is true. Using fallback rule-based analyzer.")
            fallback_system_prompt = (
                "You are an AIOps incident analysis engine.\n\n"
                "Your job is to analyze a crawler failure and recommend ONE predefined remediation action.\n\n"
                "You may ONLY recommend one action from the following approved actions:\n"
                "- database_health_check\n"
                "- retry_crawler\n"
                "- notify_devops\n"
                "- restart_crawler"
            )
            return self._fallback_demo_analysis(incident, prompt=prompt, system_prompt=fallback_system_prompt)
        system_content = (
            "You are an AIOps incident analysis engine.\n\n"
            "Your job is to analyze a crawler failure and recommend ONE predefined remediation action.\n\n"
            "You are NOT allowed to generate shell commands, PowerShell commands, Python code, SQL, MongoDB commands, or any other executable instructions.\n\n"
            "You may ONLY recommend one action from the following approved actions:\n"
            "- database_health_check\n"
            "- retry_crawler\n"
            "- notify_devops\n"
            "- restart_crawler\n\n"
            "Analyze the incident using:\n"
            "- crawler information\n"
            "- failure category\n"
            "- failure message\n"
            "- failure event\n"
            "- complete related log sequence\n\n"
            "Determine:\n"
            "1. What most likely caused the failure.\n"
            "2. The failure category.\n"
            "3. Your confidence from 0.0 to 1.0.\n"
            "4. ONE recommended action from the approved action list.\n"
            "5. A short explanation for the recommendation.\n\n"
            "Important rules:\n"
            "- Never invent an action.\n"
            "- Never return an executable command.\n"
            "- Never recommend an action outside the approved list.\n"
            "- If the evidence is insufficient, set confidence below 0.80.\n"
            "- If confidence is below 0.80, recommend \"notify_devops\".\n"
            "- Return JSON only.\n\n"
            "The JSON output must strictly adhere to the following schema:\n"
            "{\n"
            '  "diagnosis": "<What most likely caused the failure>",\n'
            '  "failure_category": "<The failure category>",\n'
            '  "confidence": <confidence float between 0.0 and 1.0>,\n'
            '  "recommended_action": "<ONE recommended action from the approved list>",\n'
            '  "reason": "<A short explanation for the recommendation>"\n'
            "}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        # Log both prompts as structured Kibana fields (ai.prompt + ai.system_prompt)
        logger.info(
            f"Sending request to NVIDIA AI model '{self.model}'",
            extra={"ai_prompt": prompt, "ai_system_prompt": system_content}
        )

        try:
            import urllib3
            url = f"{self.base_url}/chat/completions"

            # Attempt 1: standard SSL verification
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15.0, verify=True)
            except requests.exceptions.SSLError:
                response = None

            # Attempt 2: if SSL error OR corporate proxy returned 404 (proxy interception signal)
            if response is None or (response.status_code == 404 and "page not found" in response.text.lower()):
                logger.warning("SSL verification failed or proxy 404 detected. Retrying without SSL verification (corporate proxy).")
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response = requests.post(url, json=payload, headers=headers, timeout=15.0, verify=False)

            # Log the raw AI response as a structured Kibana field (ai.raw_response)
            logger.info(
                f"NVIDIA AI raw response [status={response.status_code}]",
                extra={"ai_raw_response": response.text}
            )


            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                result = AIAnalysisResult(**data)
                result.prompt = prompt
                result.system_prompt = system_content
                result.raw_response = content
                return result
            else:
                logger.error(f"NVIDIA AI returned non-200 status: {response.status_code}. Falling back to demo analyzer.")
                return self._fallback_demo_analysis(
                    incident, prompt=prompt, system_prompt=system_content, raw_response=response.text
                )
        except Exception as e:
            logger.error(f"NVIDIA AI call failed with exception: {str(e)}. Falling back to demo analyzer.")
            return self._fallback_demo_analysis(
                incident, prompt=prompt, system_prompt=system_content
            )

    def _build_prompt(self, incident: Incident) -> str:
        logs_summary = json.dumps(incident.related_logs, indent=2)
        return (
            f"Crawler ID: {incident.crawler_id}\n"
            f"Crawler Name: {incident.crawler_name}\n"
            f"Run ID: {incident.run_id}\n"
            f"Failure Category: {incident.failure_category}\n"
            f"Failure Message: {incident.failure_message}\n"
            f"Failure Event: {json.dumps(incident.failure_event)}\n"
            f"Complete Related Logs Sequence:\n{logs_summary}\n"
        )

    def _fallback_demo_analysis(
        self,
        incident: Incident,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        raw_response: Optional[str] = None
    ) -> AIAnalysisResult:
        """
        Deterministic rule-based analysis used for offline/demo verification.
        """
        cat = incident.failure_category
        msg = incident.failure_message

        if cat in ["mongodb_connection_error", "mongodb_timeout"]:
            result = AIAnalysisResult(
                diagnosis=f"MongoDB database connection issue detected: {msg}",
                failure_category=cat,
                confidence=0.95,
                recommended_action="database_health_check",
                reason="The crawler failed while establishing connection to MongoDB. Database health check is required."
            )
        elif cat in ["database_write_error", "source_connection_error", "source_timeout"]:
            result = AIAnalysisResult(
                diagnosis=f"Transient network/write failure detected: {msg}",
                failure_category=cat,
                confidence=0.90,
                recommended_action="retry_crawler",
                reason="The failure appears transient. Retrying the crawler execution is recommended."
            )
        elif cat == "invalid_response":
            result = AIAnalysisResult(
                diagnosis=f"Upstream payload response schema error: {msg}",
                failure_category=cat,
                confidence=0.88,
                recommended_action="notify_devops",
                reason="Invalid payload structure received from source API. DevOps notification required."
            )
        elif cat == "crawler_process_error":
            result = AIAnalysisResult(
                diagnosis=f"Internal crawler process execution error: {msg}",
                failure_category=cat,
                confidence=0.85,
                recommended_action="restart_crawler",
                reason="Unexpected internal exception occurred during crawler transformation. Process restart recommended."
            )
        else:
            result = AIAnalysisResult(
                diagnosis=f"Unclassified failure condition: {msg}",
                failure_category=cat,
                confidence=0.50,  # Below threshold 0.80 to trigger MANUAL_INVESTIGATION
                recommended_action="notify_devops",
                reason="Uncertain failure category requiring manual DevOps inspection."
            )

        result.prompt = prompt
        result.system_prompt = system_prompt
        result.raw_response = raw_response
        return result

