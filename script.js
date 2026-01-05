let currentSessionId = null;
let currentQuestion = null;
let questionCount = 0;
// Use a relative path so the frontend always connects to the backend on the same port
const API_BASE = '/api';

function addMessage(text, isBot = true, isSolution = false) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isBot ? 'bot-message' : 'user-message'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isSolution) {
        contentDiv.innerHTML = text;
        contentDiv.classList.add('solution-message');
    } else {
        const p = document.createElement('p');
        p.textContent = text;
        contentDiv.appendChild(p);
    }
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString();
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    messagesDiv.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function startChat() {
    const phoneInput = document.getElementById('phone-input');
    const phoneNumber = phoneInput.value.trim();
    
    if (!phoneNumber) {
        alert('Please enter your phone number');
        return;
    }
    
    // Add user message
    addMessage(`Phone: ${phoneNumber}`, false);
    
    // Disable input
    phoneInput.disabled = true;
    document.querySelector('#phone-input-area button').disabled = true;
    
    // Update status
    document.getElementById('chat-status').textContent = 'Connecting...';
    
    try {
        const response = await fetch(`${API_BASE}/start-session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phone_number: phoneNumber })
        });

        const data = await response.json();
        
        if (data.error) {
            addMessage(`Error: ${data.error}`);
            phoneInput.disabled = false;
            document.querySelector('#phone-input-area button').disabled = false;
            document.getElementById('chat-status').textContent = 'Ready';
            return;
        }

        currentSessionId = data.session_id;
        questionCount = 0;
        
        // Show welcome message
        if (data.welcome_message) {
            addMessage(data.welcome_message);
        }
        
        // Show district info
        addMessage(`📍 District identified: ${data.district}`);
        
        if (data.factors_detected && data.factors_detected.length > 0) {
            addMessage(`🔍 Detected issues: ${data.factors_detected.join(', ')}`);
        }
        
        // Update session info
        updateSessionInfo(data);
        
        // Show first question
        if (data.initial_question) {
            questionCount = 1;
            currentQuestion = data.initial_question;
            let questionText = typeof data.initial_question === 'object' && data.initial_question.question ? data.initial_question.question : data.initial_question;
            // Add options to question text if available
            if (typeof data.initial_question === 'object' && data.initial_question.options && data.initial_question.options.length > 0) {
                questionText += "\n\n";
                data.initial_question.options.forEach((option, index) => {
                    questionText += `Press ${index + 1} for ${option}\n`;
                });
            }
            addMessage(questionText);
            showAnswerButtons(data.initial_question);
            updateProgress();
        }
        
        // Hide phone input, show answer buttons
        document.getElementById('phone-input-area').style.display = 'none';
        document.getElementById('answer-input-area').style.display = 'block';
        document.getElementById('chat-status').textContent = 'Active';
        
    } catch (error) {
        console.error('Error starting chat:', error);
    addMessage('Error connecting to server. Make sure the server is running on http://localhost:5007');
        phoneInput.disabled = false;
        document.querySelector('#phone-input-area button').disabled = false;
        document.getElementById('chat-status').textContent = 'Error';
    }
}

function showAnswerButtons(question = null) {
    document.getElementById('answer-input-area').style.display = 'block';
    
    // Check if question has options (multiple choice)
    if (question && question.options && question.options.length > 0) {
        // Show number buttons
        document.getElementById('yes-no-buttons').style.display = 'none';
        document.getElementById('number-buttons').style.display = 'flex';
        
        // Generate number buttons
        const numberButtonsDiv = document.getElementById('number-buttons');
        numberButtonsDiv.innerHTML = '';
        
        question.options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'btn-number';
            button.textContent = `${index + 1}. ${option}`;
            button.onclick = () => answerQuestion((index + 1).toString());
            numberButtonsDiv.appendChild(button);
        });
    } else {
        // Show Yes/No buttons
        document.getElementById('yes-no-buttons').style.display = 'flex';
        document.getElementById('number-buttons').style.display = 'none';
    }
}

function hideAnswerButtons() {
    document.getElementById('answer-input-area').style.display = 'none';
}

async function answerQuestion(answer) {
    if (!currentSessionId || !currentQuestion) {
        return;
    }

    // Format answer for display
    let answerText = '';
    if (answer === 'yes' || answer === 'no') {
        answerText = answer === 'yes' ? 'Yes' : 'No';
    } else if (currentQuestion.options && currentQuestion.options[parseInt(answer) - 1]) {
        answerText = `${answer}. ${currentQuestion.options[parseInt(answer) - 1]}`;
    } else {
        answerText = answer;
    }
    
    // Add user answer
    addMessage(answerText, false);
    
    // Disable buttons temporarily
    const buttons = document.querySelectorAll('.btn-yes, .btn-no, .btn-number');
    buttons.forEach(btn => btn.disabled = true);

    try {
        const response = await fetch(`${API_BASE}/answer-question`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                answer: answer,
                question_id: currentQuestion.id
            })
        });

        const data = await response.json();
        
        if (data.completed) {
            // Show solution
            hideAnswerButtons();
            if (data.early_termination) {
                addMessage(data.message || "Issue identified early. Routing to agent...", true);
            }
            displaySolution(data);
            document.getElementById('chat-status').textContent = 'Resolved';
        } else if (data.next_question) {
            // Show next question
            questionCount = data.question_number;
            currentQuestion = data.next_question;
            let questionText = data.next_question.question;
            
            // Add options to question text if available
            if (data.next_question.options && data.next_question.options.length > 0) {
                questionText += "\n\n";
                data.next_question.options.forEach((option, index) => {
                    questionText += `Press ${index + 1} for ${option}\n`;
                });
            }
            
            addMessage(questionText);
            showAnswerButtons(data.next_question);
            updateProgress();
            // Re-enable buttons
            buttons.forEach(btn => btn.disabled = false);
        } else {
            // No more questions and not completed - this shouldn't happen, but handle gracefully
            // Try to categorize and show solution
            if (data.completed) {
                displaySolution(data);
            } else {
                addMessage('Session completed. Thank you!');
            }
            hideAnswerButtons();
            document.getElementById('chat-status').textContent = 'Completed';
        }
    } catch (error) {
        console.error('Error answering question:', error);
        addMessage('Error processing your answer. Please try again.');
        buttons.forEach(btn => btn.disabled = false);
    }
}

function displaySolution(data) {
    // Format category and issue type for better display
    const formatCategory = (cat) => {
        return cat.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    };
    
    const formatIssueType = (type) => {
        return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    };
    
    const solutionHtml = `
        <div class="solution-container">
            <h4 style="margin-bottom: 20px; color: #2c3e50; font-size: 1.3em;">✅ Issue Identified & Solution</h4>
            
            <div class="solution-details">
                <div class="solution-row">
                    <span class="solution-label">Category:</span>
                    <span class="solution-value">${formatCategory(data.category || 'N/A')}</span>
                </div>
                
                <div class="solution-row">
                    <span class="solution-label">Issue Type:</span>
                    <span class="solution-value">${formatIssueType(data.issue_type || 'N/A')}</span>
                </div>
                
                <div class="solution-row">
                    <span class="solution-label">Assigned Agent:</span>
                    <span class="solution-value">${data.solution?.agent || 'General Support Agent'}</span>
                </div>
                
                <div class="solution-row">
                    <span class="solution-label">Priority:</span>
                    <span class="priority-badge priority-${data.solution?.priority || 'medium'}">${(data.solution?.priority || 'medium').toUpperCase()}</span>
                </div>
            </div>
            
            <div class="solution-content">
                <div class="solution-label" style="margin-bottom: 10px; font-size: 1.1em;">Solution:</div>
                <p class="solution-text">${data.solution?.solution || 'We have noted your concern. Our support team will contact you shortly.'}</p>
            </div>
        </div>
    `;
    
    addMessage(solutionHtml, true, true);
    
    // Add reset option
    setTimeout(() => {
        addMessage('Would you like to start a new session? Refresh the page to begin again.');
    }, 1000);
}

function updateProgress() {
    const progress = (questionCount / 5) * 100;
    document.getElementById('progress-fill').style.width = `${progress}%`;
    document.getElementById('question-count').textContent = questionCount;
}

function updateSessionInfo(data) {
    const sessionInfoDiv = document.getElementById('session-info');
    const factors = Array.isArray(data.factors_detected) ? data.factors_detected : [];
    sessionInfoDiv.innerHTML = `
        <p><strong>Session ID:</strong> ${data.session_id}</p>
        <p><strong>District:</strong> ${data.district}</p>
        <p><strong>Phone:</strong> ${data.phone_number}</p>
        <p><strong>Detected Factors:</strong> ${factors.length > 0 ? factors.join(', ') : 'None'}</p>
    `;
}

// Allow Enter key to start chat
document.getElementById('phone-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        startChat();
    }
});
