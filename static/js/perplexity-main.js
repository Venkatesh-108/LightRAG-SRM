document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const navButtons = document.querySelectorAll('.nav-button');
    const welcomeView = document.getElementById('welcome-view');
    const chatView = document.getElementById('chat-view');
    const documentsView = document.getElementById('documents-view');
    const newChatButton = document.querySelector('.new-chat-button');
    const uploadDocumentButton = document.querySelector('.upload-document-button');
    const documentGrid = document.querySelector('.document-grid');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.querySelector('.chat-messages');
    const suggestionCards = document.querySelectorAll('.suggestion-card');
    const chatItems = document.querySelectorAll('.chat-item');
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');

    let currentView = 'welcome';
    let sidebarCollapsed = false;

    // Auto-resize textarea
    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    // Initialize
    chatInput.addEventListener('input', () => autoResize(chatInput));

    // Sidebar Toggle
    sidebarToggle.addEventListener('click', () => {
        sidebarCollapsed = !sidebarCollapsed;
        sidebar.classList.toggle('collapsed', sidebarCollapsed);
        sidebarToggle.title = sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar';
    });

    // Mobile Menu Toggle
    mobileMenuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
    });

    // Close mobile menu on outside click
    document.addEventListener('click', (e) => {
        if (!sidebar.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
            sidebar.classList.remove('mobile-open');
        }
    });

    // Navigation
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const view = button.getAttribute('data-view');
            switchView(view);
            
            // Update active nav button
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });

    // Switch Views
    function switchView(view) {
        // Hide all views
        welcomeView.classList.add('hidden');
        chatView.classList.add('hidden');
        documentsView.classList.add('hidden');

        // Show selected view
        switch(view) {
            case 'chats':
                if (currentView === 'welcome') {
                    welcomeView.classList.remove('hidden');
                } else {
                    chatView.classList.remove('hidden');
                }
                break;
            case 'documents':
                documentsView.classList.remove('hidden');
                loadDocuments();
                break;
        }
        currentView = view;
    }

    // New Chat
    newChatButton.addEventListener('click', () => {
        startNewChat();
    });

    function startNewChat() {
        welcomeView.classList.add('hidden');
        chatView.classList.remove('hidden');
        chatMessages.innerHTML = '';
        chatInput.focus();
        currentView = 'chat';
    }

    // Suggestion Cards
    suggestionCards.forEach(card => {
        card.addEventListener('click', () => {
            const title = card.querySelector('h3').textContent;
            startNewChat();
            chatInput.value = `Help me with: ${title}`;
            autoResize(chatInput);
        });
    });

    // Chat Items
    chatItems.forEach(item => {
        item.addEventListener('click', () => {
            chatItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            startNewChat();
        });
    });

    // Send Message
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Disable input
        chatInput.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<div class="loading-spinner"></div>';

        // Add user message
        appendMessage(message, 'user');
        chatInput.value = '';
        autoResize(chatInput);

        // Add loading message
        const loadingMessage = appendMessage('', 'bot', true);

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: message })
            });

            const result = await response.json();
            loadingMessage.remove();
            appendMessage(result.response, 'bot');
        } catch (error) {
            console.error('Error:', error);
            loadingMessage.remove();
            appendMessage('Sorry, something went wrong. Please try again.', 'bot');
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '➤';
            chatInput.focus();
        }
    }

    function appendMessage(content, sender, isLoading = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} fade-in`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? 'U' : 'AI';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        if (isLoading) {
            messageContent.innerHTML = '<div class="loading-spinner"></div> Thinking...';
        } else {
            messageContent.textContent = content;
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return messageDiv;
    }

    // Document Upload
    uploadDocumentButton.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.pdf,.doc,.docx,.txt';
        input.multiple = true;
        
        input.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            files.forEach(file => uploadDocument(file));
        });
        
        input.click();
    });

    async function uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                loadDocuments();
            } else {
                console.error('Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
        }
    }

    // Load Documents
    async function loadDocuments() {
        try {
            const response = await fetch('/documents');
            const documents = await response.json();
            
            const countElement = document.querySelector('.document-count');
            if (countElement) {
                countElement.textContent = `${documents.length} document${documents.length !== 1 ? 's' : ''} uploaded`;
            }

            documentGrid.innerHTML = '';
            
            if (documents.length === 0) {
                documentGrid.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-secondary);">
                        <h3>No documents yet</h3>
                        <p>Upload your first document to get started</p>
                    </div>
                `;
                return;
            }

            documents.forEach(docName => {
                const card = document.createElement('div');
                card.className = 'document-card';
                
                const fileExtension = docName.split('.').pop().toLowerCase();
                const fileIcon = getFileIcon(fileExtension);
                
                card.innerHTML = `
                    <div class="document-header">
                        <div class="document-icon">${fileIcon}</div>
                        <div class="document-info">
                            <h3>${docName}</h3>
                            <p class="document-meta">PDF • ${getRandomSize()} • ${getRandomDate()}</p>
                        </div>
                    </div>
                    <div class="document-actions">
                        <button class="action-button primary" onclick="viewDocument('${docName}')">View</button>
                        <button class="action-button" onclick="downloadDocument('${docName}')">Download</button>
                        <button class="action-button" onclick="deleteDocument('${docName}')">Delete</button>
                    </div>
                `;
                
                documentGrid.appendChild(card);
            });
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    }

    function getFileIcon(extension) {
        const icons = {
            'pdf': '📄',
            'doc': '📝',
            'docx': '📝',
            'txt': '📄',
            'default': '📄'
        };
        return icons[extension] || icons.default;
    }

    function getRandomSize() {
        const sizes = ['1.2 MB', '2.5 MB', '856 KB', '3.1 MB', '1.8 MB'];
        return sizes[Math.floor(Math.random() * sizes.length)];
    }

    function getRandomDate() {
        const dates = ['2 hours ago', '1 day ago', '3 days ago', '1 week ago', '2 weeks ago'];
        return dates[Math.floor(Math.random() * dates.length)];
    }

    // Document Actions (Global functions)
    window.viewDocument = function(docName) {
        console.log('Viewing document:', docName);
        // Implement document viewing logic
    };

    window.downloadDocument = function(docName) {
        console.log('Downloading document:', docName);
        // Implement download logic
        window.open(`/download/${encodeURIComponent(docName)}`, '_blank');
    };

    window.deleteDocument = async function(docName) {
        if (confirm(`Are you sure you want to delete "${docName}"?`)) {
            try {
                const response = await fetch(`/delete/${encodeURIComponent(docName)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    loadDocuments();
                } else {
                    console.error('Delete failed');
                }
            } catch (error) {
                console.error('Delete error:', error);
            }
        }
    };

    // Search functionality
    const documentSearch = document.getElementById('document-search');
    if (documentSearch) {
        documentSearch.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const documentCards = document.querySelectorAll('.document-card');
            
            documentCards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                if (title.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Initialize with welcome view
    switchView('chats');
});
