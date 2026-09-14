import re

with open('app.js', 'r', encoding='utf-8') as f:
    code = f.read()

new_confirm = '''
function confirmAndSend() {
    logAudit("User initiated confirmation process...", "info");
    const payloadStr = document.getElementById("payload").value;
    if (!payloadStr) return;
    const payloadObj = JSON.parse(payloadStr);
    
    // Show confirmation UI
    document.getElementById("voice-transfer-container").classList.add("hidden");
    document.getElementById("confirmation-container").classList.remove("hidden");
    
    document.getElementById("confirm-recipient").innerText = payloadObj.beneficiary_reference || "N/A";
    
    const amt = payloadObj.amount ? parseFloat(payloadObj.amount).toFixed(2) : "0.00";
    document.getElementById("confirm-amount").innerText = "$" + amt + " " + (payloadObj.currency || "USD");
    
    document.getElementById("confirm-reason").innerText = payloadObj.reason || "None provided";
}

function cancelTransfer() {
    logAudit("User cancelled the transfer via UI.", "info");
    document.getElementById("confirmation-container").classList.add("hidden");
    document.getElementById("voice-transfer-container").classList.remove("hidden");
}

async function executeTransfer() {
    logAudit("[TOOL] USER CONFIRMED", "info");
    
    document.getElementById("confirmation-container").classList.add("hidden");
    document.getElementById("decision-container").classList.remove("hidden");
    
    // Clear UI
    document.getElementById("res-decision").innerText = "EVALUATING...";
    document.getElementById("res-status").innerText = "...";
    document.getElementById("res-risk").innerText = "...";
    document.getElementById("res-policy").innerText = "...";
    document.getElementById("res-reason-code").innerText = "...";
    document.getElementById("res-reason").innerText = "...";
    document.getElementById("res-action").innerText = "...";
    
    const payloadStr = document.getElementById("payload").value;
    
    try {
        const idempotencyKey = "client-gen-" + btoa(payloadStr + currentSessionId).substring(0, 20);
        logAudit("[TOOL] BACKEND REQUEST SENT", "info");
        
        const payloadObj = JSON.parse(payloadStr);
        logAudit([TOOL] OUTBOUND PAYLOAD: , "system");
        logAudit([TOOL] OUTBOUND KEYS: , "system");

        const res = await fetch(${API_BASE}/voice/intent, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": Bearer ,
                "x-voice-session-id": currentSessionId,
                "Idempotency-Key": idempotencyKey
            },
            body: payloadStr
        });
        
        let data;
        try {
            data = await res.json();
        } catch(e) {
            const errorText = await res.text();
            throw new Error(Server returned non-JSON response:  );
        }

        if (!res.ok) {
            logAudit([TOOL] SECURITY GATEWAY RESULT: ERROR, "error");
            document.getElementById("res-decision").innerText = "ERROR";
            document.getElementById("res-status").innerText = "FAILED";
            document.getElementById("res-risk").innerText = "N/A";
            document.getElementById("res-policy").innerText = "N/A";
            document.getElementById("res-reason-code").innerText = "HTTP_ERROR";
            document.getElementById("res-reason").innerText = data.detail || "An unknown error occurred.";
            document.getElementById("res-action").innerText = "Review audit logs.";
            
            // Visual coloring for error
            const decEl = document.getElementById("res-decision");
            decEl.className = "text-lg font-bold text-red-600";
            return;
        }

        logAudit([TOOL] SECURITY GATEWAY RESULT: , "success");
        logAudit([TOOL] EXECUTION RESULT:  (Reason: ), "system");
        
        document.getElementById("res-decision").innerText = data.decision;
        document.getElementById("res-status").innerText = data.status;
        
        // Handle risk score visually
        const riskScore = data.risk_score !== undefined && data.risk_score !== null ? data.risk_score : 0;
        document.getElementById("res-risk").innerText = riskScore + " / 100";
        const riskBar = document.getElementById("risk-bar-fill");
        if(riskBar) {
            riskBar.style.width = ${Math.min(100, Math.max(0, riskScore))}%;
            if (riskScore < 30) riskBar.className = "h-full bg-emerald-500 rounded-full";
            else if (riskScore < 70) riskBar.className = "h-full bg-amber-500 rounded-full";
            else riskBar.className = "h-full bg-red-500 rounded-full";
        }
        
        const riskText = document.getElementById("risk-text");
        if(riskText) {
            if (riskScore < 30) riskText.innerText = "Low risk";
            else if (riskScore < 70) riskText.innerText = "Elevated risk";
            else riskText.innerText = "High risk";
        }

        document.getElementById("res-policy").innerText = data.policy_decision || "N/A";
        document.getElementById("res-reason-code").innerText = data.reason_code || "N/A";
        document.getElementById("res-reason").innerText = data.reason || "N/A";
        document.getElementById("res-action").innerText = data.next_action || "N/A";

        // Visual coloring for decision
        const decEl = document.getElementById("res-decision");
        const decIcon = document.getElementById("decision-icon");
        
        if (data.decision === "ALLOW") {
            decEl.className = "text-lg font-bold text-emerald-600";
            if(decIcon) decIcon.innerHTML = <svg class="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>;
        } else if (data.decision === "STEP_UP" || data.decision === "STEP_UP_REQUIRED") {
            decEl.className = "text-lg font-bold text-amber-600";
            if(decIcon) decIcon.innerHTML = <svg class="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>;
        } else {
            decEl.className = "text-lg font-bold text-red-600";
            if(decIcon) decIcon.innerHTML = <svg class="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>;
        }
        
        // Return result to LLM
        if (socket && socket.readyState === WebSocket.OPEN && currentCallId) {
            logAudit([TOOL] CALL ID: , "system");
            logAudit([TOOL] FUNCTION: initiate_transfer, "system");
            
            const toolResultEvent = {
                "type": "tool.result",
                "call_id": currentCallId,
                "result": JSON.stringify(data),
                "is_error": !res.ok
            };
            
            logAudit([TOOL] RESULT EVENT: , "system");
            socket.send(JSON.stringify(toolResultEvent));
            logAudit("[TOOL] RESULT RETURNED TO AGENT", "info");
        }

    } catch (err) {
        logAudit(Transmission failed: , "error");
    }
}
'''

pattern = re.compile(r'async function confirmAndSend\(\) \{.*?\}(?=\n\n|$)', re.DOTALL)
new_code = pattern.sub(new_confirm, code)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(new_code)
