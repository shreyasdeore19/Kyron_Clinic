/**
 * Kyron Medical — Chat Interface Controller
 */
(function () {
    'use strict';

    const chatMessages = document.getElementById('chatMessages');
    const chatArea = document.getElementById('chatArea');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const resetBtn = document.getElementById('resetBtn');
    const infoBtn = document.getElementById('infoBtn');
    const infoModal = document.getElementById('infoModal');
    const closeModal = document.getElementById('closeModal');
    const voiceCallBtn = document.getElementById('voiceCallBtn');
    const voiceBanner = document.getElementById('voiceBanner');
    const endVoiceBtn = document.getElementById('endVoiceBtn');
    const smsModal = document.getElementById('smsModal');
    const closeSmsModal = document.getElementById('closeSmsModal');
    const smsOptInBtn = document.getElementById('smsOptInBtn');
    const smsDeclineBtn = document.getElementById('smsDeclineBtn');

    let isWaitingForResponse = false;
    let appointmentBooked = false;

    // ---- CSRF ----
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return value;
        }
        return '';
    }

    // ---- Auto-resize textarea ----
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
        sendBtn.disabled = !messageInput.value.trim();
    });

    // ---- Send message ----
    function sendMessage(text) {
        const msg = (text || messageInput.value).trim();
        if (!msg || isWaitingForResponse) return;

        appendMessage('user', msg);
        messageInput.value = '';
        messageInput.style.height = 'auto';
        sendBtn.disabled = true;
        isWaitingForResponse = true;

        showTypingIndicator();

        fetch('/api/send-message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ message: msg }),
        })
            .then((res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then((data) => {
                removeTypingIndicator();
                if (data.error) {
                    appendMessage('assistant', `I'm sorry, something went wrong: ${data.error}`);
                } else {
                    appendMessage('assistant', data.response, data.appointment);

                    if (data.appointment && !appointmentBooked) {
                        appointmentBooked = true;
                        setTimeout(() => showSmsOptIn(), 2000);
                    }
                }
            })
            .catch((err) => {
                removeTypingIndicator();
                appendMessage(
                    'assistant',
                    "I'm having trouble connecting right now. Please check that your Gemini API key is configured in the `.env` file and try again."
                );
                console.error('Chat error:', err);
            })
            .finally(() => {
                isWaitingForResponse = false;
            });
    }

    sendBtn.addEventListener('click', () => sendMessage());
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // ---- Quick action buttons ----
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.quick-action-btn');
        if (btn) {
            const msg = btn.dataset.message;
            if (msg) sendMessage(msg);
        }
    });

    // ---- Append message to chat ----
    function appendMessage(role, content, appointment) {
        const wrapper = document.createElement('div');
        wrapper.className = `message ${role}-message`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';

        if (role === 'assistant') {
            const faviconUrl = window.KYRON_FAVICON_URL || '';
            avatar.innerHTML = faviconUrl
                ? `<img src="${faviconUrl}" alt="Kyra" class="avatar-img">`
                : `<svg width="20" height="20" viewBox="0 0 32 32" fill="none">
                    <circle cx="16" cy="16" r="15" stroke="#00c2ff" stroke-width="2"/>
                    <path d="M10 16h12M16 10v12" stroke="#00c2ff" stroke-width="2.5" stroke-linecap="round"/>
                   </svg>`;
        } else {
            avatar.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>`;
        }

        const bubble = document.createElement('div');
        bubble.className = `message-content ${role === 'assistant' ? 'glass-message' : ''}`;
        bubble.innerHTML = formatMessage(content);

        if (appointment) {
            bubble.innerHTML += buildAppointmentCard(appointment);
        }

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);

        requestAnimationFrame(() => {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    }

    function formatMessage(text) {
        if (!text) return '';
        let html = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');

        const lines = html.split('\n');
        let result = [];
        let inList = false;

        for (const line of lines) {
            const listMatch = line.match(/^\s*\d+\.\s+(.+)/);
            if (listMatch) {
                if (!inList) { result.push('<ol>'); inList = true; }
                result.push('<li>' + listMatch[1] + '</li>');
            } else {
                if (inList) { result.push('</ol>'); inList = false; }
                result.push(line);
            }
        }
        if (inList) result.push('</ol>');

        return result
            .filter(function (l, i, a) {
                return !(l === '' && (a[i - 1] === '</ol>' || (a[i + 1] && a[i + 1].startsWith('<ol>'))));
            })
            .join('<br>');
    }

    function buildAppointmentCard(appt) {
        return `
            <div class="appointment-card">
                <h4>✅ Appointment Confirmed</h4>
                <div class="detail-row"><strong>Doctor:</strong> ${appt.doctor}</div>
                <div class="detail-row"><strong>Date:</strong> ${appt.date}</div>
                <div class="detail-row"><strong>Time:</strong> ${appt.time}</div>
                <div class="detail-row"><strong>Location:</strong> ${appt.location}</div>
            </div>`;
    }

    // ---- Typing indicator ----
    function showTypingIndicator() {
        const el = document.createElement('div');
        el.className = 'typing-indicator';
        el.id = 'typingIndicator';
        const faviconUrl = window.KYRON_FAVICON_URL || '';
        const avatarHtml = faviconUrl
            ? `<img src="${faviconUrl}" alt="Kyra" class="avatar-img">`
            : `<svg width="20" height="20" viewBox="0 0 32 32" fill="none">
                <circle cx="16" cy="16" r="15" stroke="#00c2ff" stroke-width="2"/>
                <path d="M10 16h12M16 10v12" stroke="#00c2ff" stroke-width="2.5" stroke-linecap="round"/>
               </svg>`;
        el.innerHTML = `
            <div class="message-avatar">${avatarHtml}</div>
            <div class="typing-dots"><span></span><span></span><span></span></div>`;
        chatMessages.appendChild(el);
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    // ---- Voice call ----
    voiceCallBtn.addEventListener('click', () => {
        if (isWaitingForResponse) return;

        voiceCallBtn.classList.add('calling');

        fetch('/api/voice-call/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({}),
        })
            .then((res) => res.json())
            .then((data) => {
                voiceCallBtn.classList.remove('calling');
                if (data.error) {
                    if (data.error.includes('phone number')) {
                        appendMessage('assistant',
                            "📞 I'd love to call you! Could you first share your **phone number** in the chat so I know where to reach you?"
                        );
                        messageInput.focus();
                        messageInput.placeholder = 'Enter your phone number...';
                    } else {
                        appendMessage('assistant', '📞 ' + data.error);
                    }
                } else {
                    voiceBanner.style.display = 'block';
                    appendMessage(
                        'assistant',
                        `📞 ${data.message}${data.context_summary ? '\n\n*Context transferred to voice agent.*' : ''}`
                    );
                }
            })
            .catch(() => {
                voiceCallBtn.classList.remove('calling');
                appendMessage('assistant', "📞 Couldn't initiate the voice call. Please try again.");
            });
    });

    endVoiceBtn.addEventListener('click', () => {
        voiceBanner.style.display = 'none';
        appendMessage('assistant', "Voice call ended. I'm still here if you need anything! 😊");
    });

    // ---- Info modal ----
    infoBtn.addEventListener('click', () => infoModal.classList.add('active'));
    closeModal.addEventListener('click', () => infoModal.classList.remove('active'));
    infoModal.addEventListener('click', (e) => {
        if (e.target === infoModal) infoModal.classList.remove('active');
    });

    // ---- Reset ----
    resetBtn.addEventListener('click', () => {
        fetch('/api/reset/', {
            headers: { 'X-CSRFToken': getCSRFToken() },
        })
            .then(() => location.reload())
            .catch(() => location.reload());
    });

    // ---- SMS opt-in ----
    function showSmsOptIn() {
        smsModal.classList.add('active');
    }

    closeSmsModal.addEventListener('click', () => smsModal.classList.remove('active'));
    smsDeclineBtn.addEventListener('click', () => smsModal.classList.remove('active'));
    smsOptInBtn.addEventListener('click', () => {
        fetch('/api/sms-opt-in/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({}),
        })
            .then((res) => res.json())
            .then(() => {
                smsModal.classList.remove('active');
                appendMessage('assistant', "✅ You've been opted in for SMS notifications. We'll text you appointment reminders!");
            });
    });

    smsModal.addEventListener('click', (e) => {
        if (e.target === smsModal) smsModal.classList.remove('active');
    });

    // ---- Focus input on load ----
    messageInput.focus();
})();
