const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://localhost:8000/api/v1" : "/api/v1";

let currentToken = null;
let currentSessionId = null;
let aaiToken = null;
let socket = null;
let audioContext = null;
let processor = null;
let framesSent = 0;
let eventsReceived = 0;
let fullTranscript = "";
let isRecording = false;

function logAudit(message, type = "info") {
    const log = document.getElementById("audit-log");
    if (log.innerHTML.includes("Waiting for events")) {
        log.innerHTML = "";
    }
    
    const colors = {
        info: "text-blue-400",
        success: "text-emerald-400",
        warning: "text-amber-400",
        error: "text-red-400",
        system: "text-slate-500"
    };

    const time = new Date().toISOString().split("T")[1].split(".")[0];
    const div = document.createElement("div");
    div.innerHTML = `<span class="text-slate-600">[${time}]</span> <span class="${colors[type]}">${message}</span>`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
}

async function login() {
    const email = "officer@example.com";
    const password = "password";
    
    logAudit("Authenticating user...", "info");

    try {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });

        if (!res.ok) throw new Error("Login failed");

        const data = await res.json();
        currentToken = data.access_token;
        
        const userNameEl = document.getElementById("user-name");
        if (userNameEl) userNameEl.innerText = email;
        const userRoleEl = document.getElementById("user-role");
        if (userRoleEl) userRoleEl.innerText = "Financial Officer";
        
        document.getElementById("auth-status").innerText = "Authenticated as " + email;
        document.getElementById("auth-status").className = "text-sm font-semibold bg-emerald-900 px-4 py-2 rounded-full text-emerald-300";
        document.getElementById("session-section").classList.remove("opacity-50", "pointer-events-none");
        
        logAudit(`Authentication successful. Token acquired.`, "success");

    } catch (err) {
        logAudit(err.message, "error");
    }
}

async function startVoiceSession() {
    logAudit("Initializing voice session...", "info");

    try {
        // 1. Create Voice Session
        const res = await fetch(`${API_BASE}/voice/session`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${currentToken}` }
        });

        if (!res.ok) throw new Error("Session creation failed");
        const data = await res.json();
        currentSessionId = data.session_id;

        // 2. Obtain AssemblyAI Temp Token
        const tokenRes = await fetch(`${API_BASE}/voice/token`, {
            method: "GET",
            headers: { "Authorization": `Bearer ${currentToken}` }
        });

        if (!tokenRes.ok) throw new Error("AssemblyAI Token fetch failed");
        const tokenData = await tokenRes.json();
        aaiToken = tokenData.token;

        document.getElementById("session-status").innerHTML = `<span class="text-emerald-400">Session Active:</span> ${currentSessionId}`;
        document.getElementById("voice-section").classList.remove("opacity-50", "pointer-events-none");
        
        logAudit(`Voice session bound to identity. ID: ${currentSessionId.split("-")[0]}...`, "success");
        setupMicButton();

    } catch (err) {
        logAudit(err.message, "error");
    }
}

function setupMicButton() {
    const btn = document.getElementById("record-btn");
    if (!btn) return;

    if (btn.dataset.bound === "true") return;
    btn.dataset.bound = "true";
    
    btn.addEventListener("mousedown", async () => {
        if (!aaiToken) return;
        isRecording = true;
        btn.classList.add("recording-pulse");
        document.getElementById("mic-status").innerText = "MIC LIVE";
        document.getElementById("mic-status").className = "text-xs font-bold px-2 py-1 bg-red-900 text-red-400 rounded recording-pulse";
        document.getElementById("live-transcript").innerText = "Listening...";
        fullTranscript = "";
        
        await startAssemblyAIRealtime();
    });

    btn.addEventListener("mouseup", async () => {
        isRecording = false;
        btn.classList.remove("recording-pulse");
        document.getElementById("mic-status").innerText = "MIC OFF";
        document.getElementById("mic-status").className = "text-xs font-bold px-2 py-1 bg-slate-800 text-slate-500 rounded";
        
        await stopAssemblyAIRealtime();
    });
}

async function startAssemblyAIRealtime() {
    logAudit("Connecting to AssemblyAI Voice Agent API...", "system");
    
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    
    let stream;
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        const diagMic = document.getElementById("diag-mic");
        if (diagMic) {
            diagMic.innerText = "ACTIVE";
            diagMic.className = "font-bold text-emerald-400";
        }
    } catch (err) {
        logAudit("[MIC] getUserMedia FAILED", "error");
        logAudit(`[MIC] error.name: ${err.name}`, "error");
        logAudit(`[MIC] error.message: ${err.message}`, "error");
        return;
    }
        
    try {
        if (!audioContext || audioContext.state === "closed") {
            logAudit("[AUDIO-CONTEXT] Context was destroyed before stream resolved. Aborting.", "warning");
            return;
        }
        
        logAudit("[AUDIO-CONTEXT] access", "system");
        logAudit(`[AUDIO-CONTEXT] exists=${audioContext !== null}`, "system");
        logAudit(`[AUDIO-CONTEXT] state=${audioContext.state}`, "system");
        await audioContext.audioWorklet.addModule("audio-processor.js");
        
        const diagWorklet = document.getElementById("diag-worklet");
        if (diagWorklet) {
            diagWorklet.innerText = "ACTIVE";
            diagWorklet.className = "font-bold text-emerald-400";
        }
        
        const source = audioContext.createMediaStreamSource(stream);
        processor = new AudioWorkletNode(audioContext, "pcm-processor");
        
        logAudit("[WS] constructed", "system");
        socket = new WebSocket(`wss://agents.assemblyai.com/v1/ws?token=${aaiToken}`);
        logAudit(`[WS] readyState immediately after construction: ${socket.readyState}`, "system");
        
        socket.onopen = () => {
            logAudit(`[WS] onopen fired. readyState: ${socket.readyState}`, "system");
            const diagWs = document.getElementById("diag-ws");
            if (diagWs) {
                diagWs.innerText = "CONNECTED";
                diagWs.className = "font-bold text-emerald-400";
            }
            
            socket.send(JSON.stringify({
                "type": "session.update",
                "session": {
                    "system_prompt": "You are a financial intent extraction agent. Help the user initiate a transfer. The approved beneficiary ID for BEN-001 is 00000000-0000-0000-0000-000000000001.",
                    "tools": [
                        {
                            "type": "function",
                            "name": "initiate_transfer",
                            "description": "Initiate a financial transfer to a beneficiary.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "beneficiary_reference": { "type": "string" },
                                    "amount": { "type": "number" },
                                    "currency": { "type": "string" },
                                    "reason": { "type": "string" }
                                },
                                "required": ["beneficiary_reference", "amount", "currency"]
                            }
                        }
                    ]
                }
            }));
            
            logAudit("Voice Agent connected. Configuring tool...", "info");
            logAudit("Microphone active. Streaming to Voice Agent.", "success");
            source.connect(processor);
            processor.connect(audioContext.destination);
        };
        
        processor.port.onmessage = (e) => {
            if (socket && socket.readyState === WebSocket.OPEN && isRecording) {
                const pcm16Data = e.data; // Int16Array
                const buffer = new ArrayBuffer(pcm16Data.length * 2);
                const view = new DataView(buffer);
                for (let i = 0; i < pcm16Data.length; i++) {
                    view.setInt16(i * 2, pcm16Data[i], true);
                }
                const base64Data = btoa(String.fromCharCode.apply(null, new Uint8Array(buffer)));
                
                socket.send(JSON.stringify({
                    type: "input.audio",
                    audio: base64Data
                }));
                
                framesSent++;
                const diagFrames = document.getElementById("diag-frames");
                if (diagFrames) diagFrames.innerText = framesSent;
            }
        };

        socket.onmessage = (event) => {
            logAudit("[WS] onmessage received", "system");
            eventsReceived++;
            const diagEvents = document.getElementById("diag-events");
            if (diagEvents) diagEvents.innerText = eventsReceived;
            
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (e) {
                logAudit(`[WS] Non-JSON message received`, "error");
                return;
            }
            
            logAudit(`[AAI] type=${data.type}`, "system");
            if (data.type === "error" || data.type === "session.error") {
                logAudit(`[AAI ERROR DETAILS] ${JSON.stringify(data)}`, "error");
            
                logAudit(`[AAI ERROR] ${data.error} / code: ${data.status_code}`, "error");
            }
            if (data.type === "transcript.user") {
                logAudit(`[AAI TRANSCRIPT] ${data.text}`, "success");
            }

            
            if (data.type === "transcript.user.delta") {
                fullTranscript += data.delta;
                const liveTranscript = document.getElementById("live-transcript");
                if (liveTranscript) liveTranscript.innerText = fullTranscript;
            } else if (data.type === "transcript.user") {
                logAudit(`[AAI EVENT] transcript.user`, "system");
                const liveTranscript = document.getElementById("live-transcript");
                if (liveTranscript) liveTranscript.innerText = data.text;
            } else if (data.type === "tool.call") {
                logAudit(`[AAI EVENT] tool.call received. FULL PAYLOAD: ${JSON.stringify(data)}`, "warning");
                
                if (data.function_name === "initiate_transfer" || data.name === "initiate_transfer") {
                    currentCallId = data.call_id;
                    const args = JSON.parse(data.arguments);
                    logAudit(`[TOOL] RAW ARGUMENTS: ${JSON.stringify(args)}`, "system");
                    
                    const payloadEl = document.getElementById("payload");
                    if(payloadEl) payloadEl.value = JSON.stringify(args, null, 2);
                    
                    const submitBtn = document.getElementById("submit-btn");
                    if(submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
                    }
                }
            } else {
                if (["session.updated", "session.ready", "input.speech.started", "reply.started", "reply.audio", "reply.done"].includes(data.type)) {
                    logAudit(`[AAI EVENT] ${data.type}`, "system");
                }
            }
        };
        
        socket.onerror = (error) => {
            logAudit("[WS] onerror", "error");
            const diagWs = document.getElementById("diag-ws");
            if (diagWs) {
                diagWs.innerText = "ERROR";
                diagWs.className = "font-bold text-red-400";
            }
        };
        
        socket.onclose = (event) => {
            logAudit(`[WS] onclose code=${event.code} reason=${event.reason} wasClean=${event.wasClean}`, "system");
            const diagWs = document.getElementById("diag-ws");
            if (diagWs) {
                diagWs.innerText = "CLOSED";
                diagWs.className = "font-bold text-slate-400";
            }
        };

    } catch (err) {
        logAudit(err.message, "error");
    }
}

async function stopAssemblyAIRealtime() {
    logAudit("Stopping recording... Microphone disconnected. Waiting for Agent response.", "info");
    
    // We intentionally DO NOT close the WebSocket here so the AssemblyAI 
    // agent can finish processing the utterance and trigger the tool.call.
    
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (audioContext) {
        await audioContext.close();
        audioContext = null;
    }
}async function confirmAndSend() {
    logAudit("User confirmed intent. Transmitting to Security Gateway...", "info");
    const payloadStr = document.getElementById("payload").value;
    
    // Clear UI
    document.getElementById("res-decision").innerText = "EVALUATING...";
    document.getElementById("res-status").innerText = "...";
    document.getElementById("res-reason").innerText = "...";
    
    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = true;
    submitBtn.classList.add("opacity-50", "cursor-not-allowed");

    try {
        // Enforce idempotency on the client side per session payload
        if (!currentSessionId) {
            currentSessionId = "123e4567-e89b-12d3-a456-426614174000"; // Mock UUID for manual test
        }
        const idempotencyKey = "client-gen-" + btoa(payloadStr + currentSessionId).substring(0, 20);

        const res = await fetch(`${API_BASE}/voice/intent`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${currentToken}`,
                "x-voice-session-id": currentSessionId,
                "Idempotency-Key": idempotencyKey
            },
            body: payloadStr
        });

        const data = await res.json();

        if (res.status === 422) {
            logAudit("Gateway schema validation failed (422 Unprocessable Entity)", "error");
            logAudit("Rejected due to forbidden LLM hallucinated fields (extra='forbid').", "error");
            document.getElementById("res-decision").innerText = "REJECTED";
            document.getElementById("res-decision").className = "text-lg font-bold text-red-500";
            return;
        }

        if (!res.ok) {
            logAudit(`Gateway error: ${data.detail}`, "error");
            return;
        }

        logAudit(`Gateway evaluated transaction: ${data.transaction_id}`, "success");
        logAudit(`Policy Engine Decision: ${data.decision}`, "system");
        
        document.getElementById("res-decision").innerText = data.decision;
        document.getElementById("res-status").innerText = data.status;
        document.getElementById("res-reason").innerText = data.reason_code;

        // Visual coloring
        const decEl = document.getElementById("res-decision");
        if (data.decision === "ALLOW") decEl.className = "text-lg font-bold text-emerald-500";
        else if (data.decision === "STEP_UP") decEl.className = "text-lg font-bold text-amber-500";
        else decEl.className = "text-lg font-bold text-red-500";


        // Add to Recent Transactions
        const args = JSON.parse(payloadStr);
        const tbody = document.getElementById("recent-transactions-list");
        if (tbody) {
            const dateStr = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            let statusHtml = '';
            if (data.decision === "ALLOW") {
                statusHtml = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">Approved</span>';
            } else if (data.decision === "STEP_UP") {
                statusHtml = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">Step Up</span>';
            } else {
                statusHtml = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Denied</span>';
            }
            
            const newRow = document.createElement("tr");
            newRow.innerHTML = `
                <td class="px-4 py-3 font-medium text-slate-800">${args.beneficiary_reference}</td>
                <td class="px-4 py-3">${dateStr}</td>
                <td class="px-4 py-3 text-right text-slate-900">$${args.amount.toFixed(2)}</td>
                <td class="px-4 py-3">${statusHtml}</td>
            `;
            tbody.insertBefore(newRow, tbody.firstChild);
        }
        
        setTimeout(() => {
            alert("Transaction Processed!\nDecision: " + data.decision + "\nStatus: " + data.status);
            // Hide review UI and go back to main
            document.getElementById("confirmation-container").classList.add("hidden");
            document.getElementById("voice-transfer-container").classList.remove("hidden");
            // Reset payload and UI
            document.getElementById("payload").value = "";
            document.getElementById("submit-btn").disabled = false;
            document.getElementById("submit-btn").classList.remove("opacity-50", "cursor-not-allowed");
        }, 100);


    } catch (err) {
        logAudit(`Transmission failed: ${err.message}`, "error");
    }
}

window.showReviewUI = function() {
    const payloadStr = document.getElementById("payload").value;
    try {
        if (!payloadStr) {
            const mockArgs = {
                beneficiary_reference: "BEN-001",
                amount: 500,
                currency: "USD",
                currency: "USD",
                reason: "office supplies"
            };
            document.getElementById("payload").value = JSON.stringify(mockArgs);
            document.getElementById("confirm-recipient").innerText = mockArgs.beneficiary_reference;
            document.getElementById("confirm-amount").innerText = "$" + mockArgs.amount;
            document.getElementById("confirm-reason").innerText = mockArgs.reason;
            
            document.getElementById("voice-transfer-container").classList.add("hidden");
            document.getElementById("confirmation-container").classList.remove("hidden");
            return;
        }
        const args = JSON.parse(payloadStr);
        document.getElementById("confirm-recipient").innerText = args.beneficiary_reference;
        document.getElementById("confirm-amount").innerText = "$" + args.amount;
        document.getElementById("confirm-reason").innerText = args.reason;
        
        document.getElementById("voice-transfer-container").classList.add("hidden");
        document.getElementById("confirmation-container").classList.remove("hidden");
    } catch (e) {
        console.error("Invalid payload", e);
    }
}

window.hideReviewUI = function() {
    document.getElementById("voice-transfer-container").classList.remove("hidden");
    document.getElementById("confirmation-container").classList.add("hidden");
}


// Auto-login on load
document.addEventListener('DOMContentLoaded', login);
