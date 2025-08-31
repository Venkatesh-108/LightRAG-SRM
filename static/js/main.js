document.addEventListener('DOMContentLoaded', function() {
    const navButtons = document.querySelectorAll('.nav-button');
    const views = {
        chats: document.getElementById('welcome-view'),
        documents: document.getElementById('documents-view')
    };
    const sidebars = {
        chats: document.getElementById('chats-list-view'),
        documents: document.getElementById('documents-list-view')
    };
    const chatView = document.getElementById('chat-view');
    const welcomeView = document.getElementById('welcome-view');
    const documentsView = document.getElementById('documents-view');
    const newChatButton = document.querySelector('.new-chat-button');
    const uploadDocumentButton = document.querySelector('.upload-document-button');
    const uploadPdfButton = document.querySelector('.upload-pdf-button');
    const fileUploadInput = document.getElementById('file-upload-input');
    const documentGrid = document.querySelector('.document-grid');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.querySelector('.chat-messages');
    const modelProviderSelect = document.getElementById('model-provider');

    let currentView = 'chats';

    // --- View Switching ---
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const view = button.getAttribute('data-view');
            if (view === currentView) return;

            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            sidebars[currentView].classList.add('hidden');
            views[currentView].classList.add('hidden');

            currentView = view;

            sidebars[currentView].classList.remove('hidden');
            views[currentView].classList.remove('hidden');
            chatView.classList.add('hidden');

            if (currentView === 'documents') {
                loadDocuments();
            }
        });
    });

    newChatButton.addEventListener('click', () => {
        welcomeView.classList.add('hidden');
        documentsView.classList.add('hidden');
        chatView.classList.remove('hidden');
        chatMessages.innerHTML = ''; // Clear previous messages
    });

    // --- Document Handling ---
    uploadDocumentButton.addEventListener('click', () => fileUploadInput.click());
    uploadPdfButton.addEventListener('click', () => fileUploadInput.click());

    fileUploadInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.success);
                loadDocuments();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('An error occurred during upload.');
        }
    });

    async function loadDocuments() {
        try {
            const response = await fetch('/documents');
            const documents = await response.json();
            documentGrid.innerHTML = '';
            documents.forEach(docName => {
                const card = document.createElement('div');
                card.className = 'document-card';
                card.innerHTML = `
                    <h3>${docName}</h3>
                    <button class="chat-about-button">Chat about this document</button>
                `;
                documentGrid.appendChild(card);
            });
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    }

    // --- Chat Functionality ---
    sendButton.addEventListener('click', sendQuery);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQuery();
    });

    async function sendQuery() {
        const query = chatInput.value.trim();
        if (!query) return;

        appendMessage(query, 'user');
        chatInput.value = '';

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const result = await response.json();
            appendMessage(result.response, 'bot');
        } catch (error) {
            appendMessage('Sorry, something went wrong.', 'bot');
        }
    }

    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- Model Selection ---
    modelProviderSelect.addEventListener('change', async () => {
        const selectedProvider = modelProviderSelect.value;
        try {
            const response = await fetch('/select_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_provider: selectedProvider })
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.success);
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('An error occurred while switching models.');
        }
    });

    // Initial load
    if (currentView === 'documents') {
        loadDocuments();
    }
});
