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
    let sidebarCollapsed = false;

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
            
            // Update document count
            const countElement = document.querySelector('.document-count');
            if (countElement) {
                countElement.textContent = `${documents.length} document${documents.length !== 1 ? 's' : ''} uploaded`;
            }
            
            documentGrid.innerHTML = '';
            documents.forEach(docName => {
                const card = document.createElement('div');
                card.className = 'document-card';
                
                // Generate mock metadata (in real app, this would come from backend)
                const fileSize = (Math.random() * 5 + 0.5).toFixed(1) + ' MB';
                const daysAgo = Math.floor(Math.random() * 7) + 1;
                const timeAgo = daysAgo === 1 ? '1 day ago' : `${daysAgo} days ago`;
                
                card.innerHTML = `
                    <div class="document-actions">
                        <button class="action-button view" title="View">👁</button>
                        <button class="action-button download" title="Download">⬇</button>
                        <button class="action-button delete" title="Delete">🗑</button>
                    </div>
                    <div class="document-header">
                        <div class="document-icon">📄</div>
                        <div class="document-info">
                            <h3>${docName}</h3>
                        </div>
                    </div>
                    <div class="document-meta">
                        <div class="document-size">${fileSize}</div>
                        <div class="document-date">${timeAgo}</div>
                    </div>
                    <button class="chat-about-button" data-filename="${docName}">Chat about this document</button>
                `;
                documentGrid.appendChild(card);
            });
            
            // Add event listeners for action buttons
            document.querySelectorAll('.action-button').forEach(button => {
                button.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const action = button.classList.contains('view') ? 'view' : 
                                  button.classList.contains('download') ? 'download' : 'delete';
                    const docName = button.closest('.document-card').querySelector('h3').textContent;
                    handleDocumentAction(action, docName);
                });
            });
            
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    }
    
    function handleDocumentAction(action, docName) {
        switch(action) {
            case 'view':
                console.log('View document:', docName);
                // Implement view functionality
                break;
            case 'download':
                console.log('Download document:', docName);
                // Implement download functionality
                break;
            case 'delete':
                if (confirm(`Are you sure you want to delete "${docName}"?`)) {
                    console.log('Delete document:', docName);
                    // Implement delete functionality
                }
                break;
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

        // Disable input during processing
        chatInput.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<div class="loading-spinner"></div>';

        // Add user message with animation
        appendMessage(query, 'user');
        chatInput.value = '';

        // Add loading message
        const loadingMessage = appendMessage('', 'bot', true);

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const result = await response.json();
            
            // Remove loading message
            loadingMessage.remove();
            
            // Add response with animation
            appendMessage(result.response, 'bot');
            
        } catch (error) {
            loadingMessage.remove();
            appendMessage('Sorry, something went wrong.', 'bot');
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = '<span class="send-icon">📤</span>';
            chatInput.focus();
        }
    }

    function appendMessage(text, sender, isLoading = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message fade-in`;
        
        if (isLoading) {
            messageDiv.classList.add('loading');
            messageDiv.innerHTML = 'Thinking<span class="loading-dots">...</span>';
        } else {
            messageDiv.textContent = text;
            messageDiv.classList.add('new');
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Remove animation classes after animation completes
        setTimeout(() => {
            messageDiv.classList.remove('fade-in', 'new');
        }, 300);
        
        return messageDiv;
    }

    // Enhanced input handling
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Clear All Chats functionality
    const clearChatsButton = document.querySelector('.clear-chats-button');
    if (clearChatsButton) {
        clearChatsButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all chats? This action cannot be undone.')) {
                // Clear chat history (implement based on your storage method)
                const chatsList = document.querySelector('.chats-list');
                const noChatsMessage = document.querySelector('.no-chats-message');
                
                // Remove all chat items except the current one
                const chatItems = chatsList.querySelectorAll('.chat-item');
                chatItems.forEach(item => item.remove());
                
                // Show no chats message
                noChatsMessage.classList.remove('hidden');
                
                // Clear current chat messages
                chatMessages.innerHTML = '';
                
                console.log('All chats cleared');
            }
        });
    }

    // Chat search functionality
    const chatSearchInput = document.getElementById('chat-search');
    if (chatSearchInput) {
        chatSearchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const chatItems = document.querySelectorAll('.chat-item');
            
            chatItems.forEach(item => {
                const title = item.querySelector('h4').textContent.toLowerCase();
                if (title.includes(searchTerm)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // Attachment button functionality
    const attachmentButton = document.querySelector('.attachment-button');
    if (attachmentButton) {
        attachmentButton.addEventListener('click', () => {
            // Create file input for attachments
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.pdf,.doc,.docx,.txt';
            fileInput.style.display = 'none';
            
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    // Handle file attachment (implement based on your needs)
                    console.log('File attached:', file.name);
                    // You could show a preview or add to chat input
                }
            });
            
            document.body.appendChild(fileInput);
            fileInput.click();
            document.body.removeChild(fileInput);
        });
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

    // Search functionality
    const searchInput = document.getElementById('document-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
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

    // Sidebar toggle functionality
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebarCollapsed = !sidebarCollapsed;
            
            if (sidebarCollapsed) {
                sidebar.classList.add('collapsed');
                sidebarToggle.title = 'Expand sidebar';
            } else {
                sidebar.classList.remove('collapsed');
                sidebarToggle.title = 'Collapse sidebar';
            }
            
            // Update layout
            updateLayoutForSidebar();
        });
    }
    
    // Mobile menu toggle
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
            }
        });
    }
    
    function updateLayoutForSidebar() {
        // Add any additional layout updates when sidebar is collapsed/expanded
        // This could include adjusting main content width, etc.
        
        // Trigger a resize event to help any responsive elements adjust
        window.dispatchEvent(new Event('resize'));
        
        // Update tooltips visibility based on collapsed state
        updateTooltips();
    }
    
    function updateTooltips() {
        const buttons = document.querySelectorAll('.nav-button, .new-chat-button, .clear-chats-button, .upload-document-button');
        buttons.forEach(button => {
            if (sidebarCollapsed) {
                button.setAttribute('data-tooltip', button.textContent.trim() || button.title);
            } else {
                button.removeAttribute('data-tooltip');
            }
        });
    }

    // Load documents on page load
    loadDocuments();
});
