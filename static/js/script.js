/**
 * Natural-Language Data Explorer (NLDE) v2.5 - Client Engine
 * Core frontend logic: Speech Recognition, Chart.js, Table Pagination,
 * Theme Switching, Dynamic Dataset Management, Predictive Analytics & Comparison.
 */

document.addEventListener('DOMContentLoaded', () => {
    // State Store
    const state = {
        activeTable: 'students',
        currentQuery: '',
        currentData: [],
        filteredData: [],
        columns: [],
        currentPage: 1,
        pageSize: 25,
        sortColumn: null,
        sortDirection: 'asc',
        chartInstance: null,
        predictiveChartInstance: null,
        chartSuggestion: null,
        activeChartType: 'auto',
        selectedVoiceLang: 'auto',
        isRecording: false,
        theme: localStorage.getItem('nlde_theme') || 'dark',
        allDatasets: []
    };

    // DOM Elements Cache
    const elements = {
        queryForm: document.getElementById('nl-query-form'),
        queryInput: document.getElementById('query-input'),
        btnRunQuery: document.getElementById('btn-run-query'),
        querySpinner: document.getElementById('query-spinner'),
        queryBtnIcon: document.getElementById('query-btn-icon'),
        btnClearQuery: document.getElementById('btn-clear-query'),
        btnVoiceSearch: document.getElementById('btn-voice-search'),
        voiceBanner: document.getElementById('voice-recording-banner'),
        voiceText: document.getElementById('voice-recording-text'),
        btnStopVoice: document.getElementById('btn-stop-voice'),
        micIcon: document.getElementById('mic-icon'),
        voiceStatusBadge: document.getElementById('voice-status-indicator'),
        activeDatasetPill: document.getElementById('active-dataset-pill'),
        currentDatasetLabel: document.getElementById('current-dataset-label'),
        datasetDropdownMenu: document.getElementById('dataset-dropdown-menu'),
        sampleQuestionsContainer: document.getElementById('sample-questions-container'),
        
        // Verification Box
        verifSection: document.getElementById('section-verification'),
        verifUserQuery: document.getElementById('verif-user-query'),
        verifCorrectionNotice: document.getElementById('verif-correction-notice'),
        verifCorrectedText: document.getElementById('verif-corrected-text'),
        verifSqlQuery: document.getElementById('verif-sql-query'),
        verifExplanation: document.getElementById('verif-explanation'),
        badgeConfidence: document.getElementById('badge-confidence-score'),
        badgeLang: document.getElementById('badge-detected-lang'),
        badgeTarget: document.getElementById('badge-query-target'),
        verifTimestamp: document.getElementById('verif-timestamp'),
        btnCopySql: document.getElementById('btn-copy-sql'),
        copySqlText: document.getElementById('copy-sql-text'),
        
        // Unsafe alert
        unsafeAlert: document.getElementById('unsafe-query-alert'),
        unsafeAlertTitle: document.getElementById('unsafe-alert-title'),
        unsafeAlertMsg: document.getElementById('unsafe-alert-message'),
        btnCloseUnsafeAlert: document.getElementById('btn-close-unsafe-alert'),
        
        // Table & Controls
        tableHead: document.getElementById('table-head'),
        tableBody: document.getElementById('table-body'),
        tableEmpty: document.getElementById('table-empty-state'),
        tableFilterInput: document.getElementById('table-filter-input'),
        rowCountBadge: document.getElementById('result-row-count-badge'),
        paginationInfo: document.getElementById('pagination-info'),
        pageSizeSelect: document.getElementById('page-size-select'),
        tablePagination: document.getElementById('table-pagination'),
        
        // Visualizations & Insights
        chartCanvas: document.getElementById('mainChartCanvas'),
        chartCardTitle: document.getElementById('chart-card-title'),
        btnDownloadChart: document.getElementById('btn-download-chart'),
        insightsList: document.getElementById('insights-list'),
        chartTypeButtons: document.querySelectorAll('.chart-type-btn'),
        
        // Modals & Offcanvas
        schemaModal: document.getElementById('schemaModal'),
        schemaModalContent: document.getElementById('schema-modal-content'),
        qualityModal: document.getElementById('qualityModal'),
        qualityModalContent: document.getElementById('quality-modal-content'),
        historyOffcanvas: document.getElementById('historyOffcanvas'),
        historyList: document.getElementById('history-list'),
        historyEmpty: document.getElementById('history-empty'),
        historyBadgeCount: document.getElementById('history-badge-count'),
        
        // Enhanced Upload & Dataset Manager Elements
        uploadModal: document.getElementById('uploadModal'),
        datasetUploadForm: document.getElementById('dataset-upload-form'),
        dragDropZone: document.getElementById('drag-drop-zone'),
        datasetFileInput: document.getElementById('dataset-file-input'),
        uploadTableNameInput: document.getElementById('upload-table-name-input'),
        selectedFileName: document.getElementById('selected-file-name'),
        uploadProgressContainer: document.getElementById('upload-progress-container'),
        uploadProgressBar: document.getElementById('upload-progress-bar'),
        uploadProgressPct: document.getElementById('upload-progress-pct'),
        uploadProgressStatus: document.getElementById('upload-progress-status'),
        btnSubmitUpload: document.getElementById('btn-submit-upload'),
        uploadResultBox: document.getElementById('upload-result-box'),
        uploadAiSummary: document.getElementById('upload-ai-summary'),
        btnViewUploadedPreview: document.getElementById('btn-view-uploaded-preview'),
        btnStartQueryingUpload: document.getElementById('btn-start-querying-upload'),

        // Dataset Manager Modal
        datasetManagerModal: document.getElementById('datasetManagerModal'),
        datasetSearchInput: document.getElementById('dataset-search-input'),
        datasetsManagerTbody: document.getElementById('datasets-manager-tbody'),

        // Dataset Preview Modal
        previewModal: document.getElementById('previewModal'),
        previewModalTableName: document.getElementById('preview-modal-table-name'),
        previewThead: document.getElementById('preview-thead'),
        previewTbody: document.getElementById('preview-tbody'),

        // Predictive Analytics Modal
        predictiveModal: document.getElementById('predictiveModal'),
        predictiveModalBody: document.getElementById('predictive-modal-body'),

        // Dataset Compare Modal
        compareModal: document.getElementById('compareModal'),
        compareSelect1: document.getElementById('compare-select-1'),
        compareSelect2: document.getElementById('compare-select-2'),
        btnRunComparison: document.getElementById('btn-run-comparison'),
        comparisonResultsContainer: document.getElementById('comparison-results-container'),
        
        // Theme
        btnThemeToggle: document.getElementById('btn-theme-toggle'),
        themeIcon: document.getElementById('theme-icon'),
        
        // Toast
        liveToast: document.getElementById('liveToast'),
        toastMessage: document.getElementById('toast-message')
    };

    // ==========================================
    // THEME CONTROLLER
    // ==========================================
    function applyTheme(theme) {
        state.theme = theme;
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('nlde_theme', theme);
        
        if (theme === 'dark') {
            elements.themeIcon.className = 'bi bi-sun-fill text-warning';
        } else {
            elements.themeIcon.className = 'bi bi-moon-stars-fill text-secondary';
        }
        
        if (state.chartInstance && state.chartSuggestion) {
            renderChart(state.chartSuggestion, state.activeChartType);
        }
    }

    elements.btnThemeToggle.addEventListener('click', () => {
        const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme);
    });

    applyTheme(state.theme);

    // ==========================================
    // TOAST NOTIFICATIONS
    // ==========================================
    const bsToast = new bootstrap.Toast(elements.liveToast, { delay: 3500 });
    function showToast(message, isError = false) {
        elements.toastMessage.textContent = message;
        elements.liveToast.className = `toast align-items-center ${isError ? 'text-bg-danger' : 'text-bg-primary'} border-0 shadow`;
        bsToast.show();
    }

    // ==========================================
    // SPEECH RECOGNITION (ENGLISH & TAMIL)
    // ==========================================
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = () => {
            state.isRecording = true;
            elements.btnVoiceSearch.classList.add('listening');
            elements.micIcon.className = 'bi bi-mic-fill text-danger';
            elements.voiceBanner.classList.remove('d-none');
            elements.voiceBanner.classList.add('d-flex');
            elements.voiceStatusBadge.innerHTML = '<span class="pulsing-recording-dot me-1"></span>Listening...';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            elements.queryInput.value = transcript;
            elements.btnClearQuery.classList.remove('d-none');
            showToast(`Voice input captured: "${transcript}"`);
            stopVoiceRecognition();
            executeQuery(transcript);
        };

        recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            showToast(`Voice recognition error: ${event.error}`, true);
            stopVoiceRecognition();
        };

        recognition.onend = () => {
            stopVoiceRecognition();
        };
    } else {
        elements.voiceStatusBadge.innerHTML = '<i class="bi bi-mic-mute me-1"></i>Speech API Unavailable';
        elements.btnVoiceSearch.setAttribute('disabled', 'true');
        elements.btnVoiceSearch.title = 'Speech Recognition is not supported by your browser';
    }

    function startVoiceRecognition() {
        if (!recognition) return;
        const lang = state.selectedVoiceLang === 'auto' ? 'en-US' : state.selectedVoiceLang;
        recognition.lang = lang;
        try {
            recognition.start();
        } catch (e) {
            console.error(e);
        }
    }

    function stopVoiceRecognition() {
        state.isRecording = false;
        elements.btnVoiceSearch.classList.remove('listening');
        elements.micIcon.className = 'bi bi-mic-fill';
        elements.voiceBanner.classList.add('d-none');
        elements.voiceBanner.classList.remove('d-flex');
        elements.voiceStatusBadge.innerHTML = '<i class="bi bi-broadcast me-1"></i>Speech Ready';
        if (recognition) {
            try { recognition.stop(); } catch (e) {}
        }
    }

    elements.btnVoiceSearch.addEventListener('click', () => {
        if (state.isRecording) {
            stopVoiceRecognition();
        } else {
            startVoiceRecognition();
        }
    });

    elements.btnStopVoice.addEventListener('click', stopVoiceRecognition);

    // Language Dropdown Selection
    document.querySelectorAll('.lang-select-opt').forEach(opt => {
        opt.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.lang-select-opt').forEach(el => el.classList.remove('active'));
            opt.classList.add('active');
            state.selectedVoiceLang = opt.getAttribute('data-lang');
            document.getElementById('selected-lang-label').textContent = opt.textContent;
            showToast(`Language set to: ${opt.textContent}`);
        });
    });

    // ==========================================
    // DYNAMIC DATASET MANAGER & SWITCHER
    // ==========================================
    async function loadDatasetsList() {
        try {
            const resp = await fetch('/datasets');
            const data = await resp.json();
            if (!data.success) return;

            state.allDatasets = data.datasets || [];
            state.activeTable = data.active_dataset || 'students';
            updateActiveDatasetUI();
        } catch (err) {
            console.error('Failed to load datasets list:', err);
        }
    }

    function updateActiveDatasetUI() {
        elements.currentDatasetLabel.textContent = state.activeTable;
        elements.activeDatasetPill.textContent = state.activeTable;
        elements.badgeTarget.textContent = `Table: ${state.activeTable}`;

        // Populate dropdown menu in navbar
        let dropHtml = '<li class="dropdown-header text-uppercase small fw-bold">Available Datasets</li>';
        state.allDatasets.forEach(d => {
            const isActive = (d.table_name === state.activeTable);
            dropHtml += `
                <li>
                    <a class="dropdown-item d-flex justify-content-between align-items-center switch-dataset-opt ${isActive ? 'active fw-bold' : ''}" 
                       href="#" data-table="${d.table_name}">
                        <span><i class="bi bi-${d.is_default ? 'mortarboard' : 'table'} me-2"></i>${d.display_name}</span>
                        <span class="badge ${isActive ? 'bg-light text-primary' : 'bg-secondary-subtle text-body-secondary'} rounded-pill ms-2">${d.row_count}</span>
                    </a>
                </li>
            `;
        });

        dropHtml += `
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-primary" href="#" data-bs-toggle="modal" data-bs-target="#uploadModal"><i class="bi bi-cloud-arrow-up me-2"></i>Upload New Dataset</a></li>
            <li><a class="dropdown-item text-secondary" href="#" data-bs-toggle="modal" data-bs-target="#datasetManagerModal"><i class="bi bi-folder2-open me-2"></i>Manage All Datasets</a></li>
        `;
        elements.datasetDropdownMenu.innerHTML = dropHtml;

        // Dropdown Click Handlers
        elements.datasetDropdownMenu.querySelectorAll('.switch-dataset-opt').forEach(opt => {
            opt.addEventListener('click', (e) => {
                e.preventDefault();
                const targetTable = opt.getAttribute('data-table');
                switchActiveDataset(targetTable);
            });
        });

        // Populate Comparison selects
        updateComparisonSelects();

        // Render contextual sample questions
        renderSampleQuestions();
    }

    async function switchActiveDataset(tableName) {
        if (state.activeTable === tableName) return;

        try {
            const resp = await fetch('/datasets/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table: tableName })
            });
            const data = await resp.json();
            if (data.success) {
                state.activeTable = tableName;
                showToast(`Switched active dataset to: ${tableName}`);
                updateActiveDatasetUI();
                await loadDashboardAnalytics();
                // Execute initial query on the new table
                const initQuery = (tableName === 'students') ? 'Show all students' : 'Show all records';
                elements.queryInput.value = initQuery;
                executeQuery(initQuery);
            }
        } catch (err) {
            console.error('Failed to switch dataset:', err);
        }
    }

    function updateComparisonSelects() {
        let optHtml = '';
        state.allDatasets.forEach(d => {
            optHtml += `<option value="${d.table_name}">${d.display_name} (${d.row_count} rows, ${d.column_count} cols)</option>`;
        });
        elements.compareSelect1.innerHTML = optHtml;
        elements.compareSelect2.innerHTML = optHtml;
        if (state.allDatasets.length >= 2) {
            elements.compareSelect2.selectedIndex = 1;
        }
    }

    // ==========================================
    // CONTEXTUAL SAMPLE QUESTIONS GENERATOR
    // ==========================================
    function renderSampleQuestions() {
        let samples = [];
        if (state.activeTable === 'students') {
            samples = [
                { text: "Show all students", label: "Show all students", tamil: false },
                { text: "Show students from Erode", label: "Students from Erode", tamil: false },
                { text: "Average CGPA", label: "Average CGPA", tamil: false },
                { text: "Top 10 students", label: "Top 10 students", tamil: false },
                { text: "Department-wise count", label: "Department-wise count", tamil: false },
                { text: "Highest CGPA", label: "Highest CGPA", tamil: false },
                { text: "Students with CGPA above 8", label: "CGPA above 8", tamil: false },
                { text: "Top students in IT", label: "Top students in IT", tamil: false },
                { text: "மாணவர்களை காட்டு", label: "மாணவர்களை காட்டு", tamil: true },
                { text: "ஈரோட்டிலிருந்து மாணவர்களை காட்டு", label: "ஈரோடு மாணவர்கள்", tamil: true },
                { text: "8 CGPA க்கு மேல் உள்ள மாணவர்கள்", label: "8 CGPA க்கு மேல்", tamil: true }
            ];
        } else {
            // Find dataset metadata
            const meta = state.allDatasets.find(d => d.table_name === state.activeTable);
            const cols = meta ? meta.columns : [];
            samples = [
                { text: "Show all records", label: "Show all records", tamil: false },
                { text: "Count total records", label: "Total count", tamil: false }
            ];

            if (cols.length > 0) {
                samples.push({ text: `${cols[0]} wise count`, label: `${cols[0]} wise`, tamil: false });
            }
            if (cols.length > 1) {
                samples.push({ text: `Average of ${cols[1]}`, label: `Average ${cols[1]}`, tamil: false });
                samples.push({ text: `Highest ${cols[1]}`, label: `Highest ${cols[1]}`, tamil: false });
            }
            samples.push({ text: "Top 5 records", label: "Top 5 records", tamil: false });
            samples.push({ text: "பதிவுகளை காட்டு", label: "அனைத்தையும் காட்டு (Tamil)", tamil: true });
        }

        let html = '<span class="small text-muted fw-semibold"><i class="bi bi-lightbulb-fill text-warning me-1"></i>Sample Questions:</span>';
        samples.forEach(s => {
            html += `<button type="button" class="sample-chip ${s.tamil ? 'chip-tamil' : ''}" data-sample="${s.text}">${s.label}</button>`;
        });
        elements.sampleQuestionsContainer.innerHTML = html;

        // Rebind click handlers
        elements.sampleQuestionsContainer.querySelectorAll('.sample-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const sampleText = chip.getAttribute('data-sample');
                elements.queryInput.value = sampleText;
                elements.btnClearQuery.classList.remove('d-none');
                executeQuery(sampleText);
            });
        });
    }

    // ==========================================
    // DRAG-AND-DROP FILE UPLOAD HANDLERS
    // ==========================================
    const dropZone = elements.dragDropZone;
    const fileInput = elements.datasetFileInput;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleSelectedFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    function handleSelectedFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['csv', 'xlsx', 'xls'].includes(ext)) {
            showToast('Invalid file format. Please choose a CSV (.csv) or Excel (.xlsx, .xls) file.', true);
            return;
        }

        elements.selectedFileName.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        elements.selectedFileName.classList.remove('d-none');

        // Auto-fill suggested table name if blank
        if (!elements.uploadTableNameInput.value) {
            const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
            elements.uploadTableNameInput.value = cleanName;
        }
    }

    // Submit File Upload Form with Real-time Progress Bar
    elements.datasetUploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const file = fileInput.files[0] || (dropZone.droppedFile);
        if (!file) {
            showToast('Please select a file to upload.', true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('table_name', elements.uploadTableNameInput.value.trim());

        // Show progress bar
        elements.uploadProgressContainer.classList.remove('d-none');
        elements.btnSubmitUpload.disabled = true;
        elements.uploadProgressBar.style.width = '0%';
        elements.uploadProgressPct.textContent = '0%';
        elements.uploadProgressStatus.textContent = 'Uploading spreadsheet...';

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/datasets/upload', true);

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                elements.uploadProgressBar.style.width = `${percent}%`;
                elements.uploadProgressPct.textContent = `${percent}%`;
                if (percent === 100) {
                    elements.uploadProgressStatus.textContent = 'Indexing in SQLite database & generating AI profile...';
                }
            }
        };

        xhr.onload = () => {
            elements.btnSubmitUpload.disabled = false;
            if (xhr.status === 200) {
                const res = JSON.parse(xhr.responseText);
                elements.uploadProgressBar.classList.remove('bg-primary');
                elements.uploadProgressBar.classList.add('bg-success');
                elements.uploadProgressStatus.textContent = 'Ingestion Complete!';

                // Display result card
                elements.uploadAiSummary.innerHTML = res.ai_summary;
                elements.uploadResultBox.classList.remove('d-none');
                showToast(`Dataset '${res.table_name}' uploaded and ready!`);

                // Update active dataset
                state.activeTable = res.table_name;
                loadDatasetsList();
                loadDashboardAnalytics();

                // Setup result action buttons
                elements.btnViewUploadedPreview.onclick = () => {
                    const bsModal = bootstrap.Modal.getInstance(elements.uploadModal);
                    if (bsModal) bsModal.hide();
                    openDatasetPreview(res.table_name);
                };

                elements.btnStartQueryingUpload.onclick = () => {
                    const bsModal = bootstrap.Modal.getInstance(elements.uploadModal);
                    if (bsModal) bsModal.hide();
                    executeQuery('Show all records');
                };

            } else {
                let err = 'Upload failed.';
                try {
                    const r = JSON.parse(xhr.responseText);
                    err = r.error || err;
                } catch (e) {}
                elements.uploadProgressBar.classList.remove('bg-primary');
                elements.uploadProgressBar.classList.add('bg-danger');
                elements.uploadProgressStatus.textContent = `Error: ${err}`;
                showToast(err, true);
            }
        };

        xhr.onerror = () => {
            elements.btnSubmitUpload.disabled = false;
            elements.uploadProgressStatus.textContent = 'Network error during upload.';
            showToast('Network error during file upload.', true);
        };

        xhr.send(formData);
    });

    // ==========================================
    // DATASET MANAGER MODAL (CRUD OPERATIONS)
    // ==========================================
    elements.datasetManagerModal.addEventListener('show.bs.modal', async () => {
        renderDatasetManagerTable();
    });

    function renderDatasetManagerTable() {
        const query = elements.datasetSearchInput.value.toLowerCase().trim();
        const filtered = state.allDatasets.filter(d => 
            d.table_name.toLowerCase().includes(query) || 
            d.display_name.toLowerCase().includes(query) ||
            d.file_name.toLowerCase().includes(query)
        );

        let html = '';
        if (filtered.length === 0) {
            html = `<tr><td colspan="7" class="text-center py-4 text-muted">No datasets found matching your search.</td></tr>`;
        } else {
            filtered.forEach(d => {
                const isActive = (d.table_name === state.activeTable);
                html += `
                    <tr class="${isActive ? 'table-primary-subtle' : ''}">
                        <td>
                            ${isActive ? '<span class="badge bg-success rounded-pill"><i class="bi bi-check-lg me-1"></i>Active</span>' : '<span class="badge bg-secondary rounded-pill">Inactive</span>'}
                        </td>
                        <td>
                            <div class="fw-bold">${d.display_name}</div>
                            <div class="small font-monospace text-muted">${d.table_name}</div>
                        </td>
                        <td><span class="badge bg-primary-subtle text-primary">${d.row_count.toLocaleString()}</span></td>
                        <td><span class="badge bg-info-subtle text-info">${d.column_count}</span></td>
                        <td><span class="small font-monospace">${d.file_name}</span> <span class="small text-muted">(${d.file_size_kb} KB)</span></td>
                        <td><span class="small text-muted">${d.uploaded_date}</span></td>
                        <td class="text-end">
                            <div class="btn-group btn-group-sm">
                                ${!isActive ? `<button class="btn btn-outline-primary btn-set-active" data-table="${d.table_name}" title="Set as Active Dataset"><i class="bi bi-play-circle"></i></button>` : ''}
                                <button class="btn btn-outline-secondary btn-mgr-preview" data-table="${d.table_name}" title="Preview Rows"><i class="bi bi-eye"></i></button>
                                ${!d.is_default ? `<button class="btn btn-outline-warning btn-mgr-rename" data-table="${d.table_name}" title="Rename Dataset"><i class="bi bi-pencil"></i></button>` : ''}
                                <button class="btn btn-outline-danger btn-mgr-delete" data-table="${d.table_name}" title="${d.is_default ? 'Reset Students Dataset' : 'Delete Dataset'}"><i class="bi bi-trash"></i></button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        }
        elements.datasetsManagerTbody.innerHTML = html;

        // Bind Action Listeners
        elements.datasetsManagerTbody.querySelectorAll('.btn-set-active').forEach(b => {
            b.addEventListener('click', () => {
                const tbl = b.getAttribute('data-table');
                switchActiveDataset(tbl);
                renderDatasetManagerTable();
            });
        });

        elements.datasetsManagerTbody.querySelectorAll('.btn-mgr-preview').forEach(b => {
            b.addEventListener('click', () => {
                const tbl = b.getAttribute('data-table');
                openDatasetPreview(tbl);
            });
        });

        elements.datasetsManagerTbody.querySelectorAll('.btn-mgr-rename').forEach(b => {
            b.addEventListener('click', () => {
                const tbl = b.getAttribute('data-table');
                promptRenameDataset(tbl);
            });
        });

        elements.datasetsManagerTbody.querySelectorAll('.btn-mgr-delete').forEach(b => {
            b.addEventListener('click', () => {
                const tbl = b.getAttribute('data-table');
                confirmDeleteDataset(tbl);
            });
        });
    }

    elements.datasetSearchInput.addEventListener('input', renderDatasetManagerTable);

    async function promptRenameDataset(oldTable) {
        const newName = prompt(`Enter new name for dataset '${oldTable}':`, oldTable);
        if (!newName || newName.trim() === oldTable) return;

        try {
            const resp = await fetch(`/datasets/${oldTable}/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newName.trim() })
            });
            const data = await resp.json();
            if (data.success) {
                showToast(data.message);
                if (state.activeTable === oldTable) {
                    state.activeTable = data.new_table;
                }
                await loadDatasetsList();
                renderDatasetManagerTable();
            } else {
                showToast(data.error || 'Failed to rename dataset.', true);
            }
        } catch (e) {
            showToast('Error during rename request.', true);
        }
    }

    async function confirmDeleteDataset(table) {
        const isDefault = (table === 'students');
        const confirmMsg = isDefault 
            ? "Are you sure you want to reset the default 'students' dataset to its original seed records?"
            : `Are you sure you want to permanently delete dataset '${table}' and its stored file?`;

        if (!confirm(confirmMsg)) return;

        try {
            const resp = await fetch(`/datasets/${table}`, { method: 'DELETE' });
            const data = await resp.json();
            if (data.success) {
                showToast(data.message);
                await loadDatasetsList();
                await loadDashboardAnalytics();
                renderDatasetManagerTable();
                executeQuery('Show all students');
            } else {
                showToast(data.error || 'Failed to delete dataset.', true);
            }
        } catch (e) {
            showToast('Error during delete request.', true);
        }
    }

    // ==========================================
    // DATASET PREVIEW MODAL
    // ==========================================
    async function openDatasetPreview(tableName) {
        elements.previewModalTableName.textContent = tableName;
        elements.previewThead.innerHTML = '';
        elements.previewTbody.innerHTML = `<tr><td class="text-center py-4"><div class="spinner-border text-primary" role="status"></div></td></tr>`;

        const bsModal = new bootstrap.Modal(elements.previewModal);
        bsModal.show();

        try {
            const resp = await fetch(`/datasets/${tableName}/preview`);
            const data = await resp.json();
            if (!data.success) {
                elements.previewTbody.innerHTML = `<tr><td class="text-danger p-3">Error: ${data.error}</td></tr>`;
                return;
            }

            const cols = data.columns || [];
            const rows = data.rows || [];

            let headHtml = '<tr>';
            cols.forEach(c => {
                headHtml += `<th>${c.replace('_', ' ').toUpperCase()}</th>`;
            });
            headHtml += '</tr>';
            elements.previewThead.innerHTML = headHtml;

            let bodyHtml = '';
            rows.forEach(r => {
                bodyHtml += '<tr>';
                cols.forEach(c => {
                    const val = r[c];
                    bodyHtml += `<td>${val !== null && val !== undefined ? val : '-'}</td>`;
                });
                bodyHtml += '</tr>';
            });
            elements.previewTbody.innerHTML = bodyHtml;

        } catch (e) {
            elements.previewTbody.innerHTML = `<tr><td class="text-danger p-3">Failed to load preview: ${e}</td></tr>`;
        }
    }

    // ==========================================
    // PREDICTIVE ANALYTICS & REGRESSION MODAL
    // ==========================================
    elements.predictiveModal.addEventListener('show.bs.modal', async () => {
        elements.predictiveModalBody.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-info" role="status"></div>
                <p class="text-muted mt-2">Computing regression trendlines and predictive models for '${state.activeTable}'...</p>
            </div>
        `;

        try {
            const resp = await fetch(`/datasets/${state.activeTable}/predictive`);
            const data = await resp.json();
            if (!data.success) {
                elements.predictiveModalBody.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                return;
            }

            const pred = data.predictive;
            if (!pred.has_numeric) {
                elements.predictiveModalBody.innerHTML = `
                    <div class="alert alert-warning text-center py-4">
                        <i class="bi bi-info-circle fs-2"></i>
                        <h6 class="mt-2 fw-bold">Predictive Modeling Unavailable</h6>
                        <p class="mb-0 small text-muted">${pred.message}</p>
                    </div>
                `;
                return;
            }

            const reg = pred.regression;
            const stats = pred.descriptive_stats;
            const corrs = pred.correlations.top_correlations;

            let html = `
                <!-- Regression Model Overview Card -->
                <div class="row g-3 mb-4">
                    <div class="col-12 col-lg-8">
                        <div class="card border h-100 shadow-sm">
                            <div class="card-header bg-transparent d-flex justify-content-between align-items-center">
                                <h6 class="fw-bold mb-0 text-primary"><i class="bi bi-graph-up me-2"></i>Linear Regression Trendline & 5-Step Forecast</h6>
                                <span class="badge bg-primary-subtle text-primary">R² = ${reg ? reg.r2_score : '0.00'}</span>
                            </div>
                            <div class="card-body p-3">
                                <div class="chart-wrapper" style="height: 280px; position: relative;">
                                    <canvas id="predictiveChartCanvas"></canvas>
                                </div>
                                ${reg ? `
                                    <div class="mt-3 p-2 bg-body-tertiary rounded small d-flex justify-content-between align-items-center flex-wrap gap-2">
                                        <div class="font-monospace fw-bold text-primary">${reg.equation}</div>
                                        <div class="text-muted">Slope: <strong>${reg.slope}</strong> | Intercept: <strong>${reg.intercept}</strong></div>
                                    </div>
                                    <p class="small text-muted mt-2 mb-0"><i class="bi bi-stars text-warning me-1"></i><strong>AI Prediction Insight:</strong> ${reg.narrative}</p>
                                ` : '<p class="text-muted small">Insufficient variance for regression.</p>'}
                            </div>
                        </div>
                    </div>

                    <!-- Top Correlated Pairs Column -->
                    <div class="col-12 col-lg-4">
                        <div class="card border h-100 shadow-sm">
                            <div class="card-header bg-transparent">
                                <h6 class="fw-bold mb-0 text-info"><i class="bi bi-diagram-2 me-2"></i>Top Correlations</h6>
                            </div>
                            <div class="card-body p-0">
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover mb-0">
                                        <thead class="table-light">
                                            <tr>
                                                <th>Feature Pair</th>
                                                <th class="text-end">Pearson (r)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
            `;

            if (corrs.length === 0) {
                html += `<tr><td colspan="2" class="text-center py-3 text-muted">Need >= 2 numeric columns</td></tr>`;
            } else {
                corrs.forEach(c => {
                    const badgeClass = c.correlation >= 0.7 ? 'corr-strong-pos' : (c.correlation > 0 ? 'corr-mod-pos' : (c.correlation <= -0.7 ? 'corr-strong-neg' : 'corr-mod-neg'));
                    html += `
                        <tr>
                            <td>
                                <div class="fw-semibold small">${c.col1}</div>
                                <div class="small text-muted font-monospace">&amp; ${c.col2}</div>
                            </td>
                            <td class="text-end align-middle">
                                <span class="corr-pill ${badgeClass}">${c.correlation > 0 ? '+' : ''}${c.correlation.toFixed(3)}</span>
                            </td>
                        </tr>
                    `;
                });
            }

            html += `
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Descriptive Statistics Table -->
                <h6 class="fw-bold mb-2 text-secondary"><i class="bi bi-calculator me-2"></i>Descriptive Statistics & Outlier Audit</h6>
                <div class="table-responsive border rounded mb-2">
                    <table class="table table-sm table-striped align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Numeric Feature</th>
                                <th class="text-end">Mean</th>
                                <th class="text-end">Std Dev</th>
                                <th class="text-end">Min</th>
                                <th class="text-end">Median</th>
                                <th class="text-end">Max</th>
                                <th class="text-end">Skewness</th>
                                <th class="text-end">Outliers (1.5 IQR)</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            for (const [colName, s] of Object.entries(stats)) {
                html += `
                    <tr>
                        <td class="fw-bold text-primary font-monospace">${colName}</td>
                        <td class="text-end">${s.mean.toLocaleString()}</td>
                        <td class="text-end">${s.std.toLocaleString()}</td>
                        <td class="text-end">${s.min.toLocaleString()}</td>
                        <td class="text-end">${s.median.toLocaleString()}</td>
                        <td class="text-end">${s.max.toLocaleString()}</td>
                        <td class="text-end">${s.skewness}</td>
                        <td class="text-end">
                            <span class="badge ${s.outliers_count > 0 ? 'bg-warning-subtle text-warning' : 'bg-success-subtle text-success'} rounded-pill">
                                ${s.outliers_count} ${s.outliers_count === 1 ? 'outlier' : 'outliers'}
                            </span>
                        </td>
                    </tr>
                `;
            }

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            elements.predictiveModalBody.innerHTML = html;

            // Render Chart.js Predictive Chart
            if (reg && reg.actual_points) {
                renderPredictiveRegressionChart(reg);
            }

        } catch (e) {
            elements.predictiveModalBody.innerHTML = `<div class="alert alert-danger">Error rendering predictive analytics: ${e}</div>`;
        }
    });

    function renderPredictiveRegressionChart(reg) {
        const canvas = document.getElementById('predictiveChartCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (state.predictiveChartInstance) {
            state.predictiveChartInstance.destroy();
        }

        const isDark = state.theme === 'dark';
        const textColor = isDark ? '#cbd5e1' : '#475569';
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';

        state.predictiveChartInstance = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: 'Actual Data Points',
                        data: reg.actual_points,
                        backgroundColor: 'rgba(59, 130, 246, 0.75)',
                        borderColor: '#2563eb',
                        pointRadius: 4.5,
                        pointHoverRadius: 6
                    },
                    {
                        type: 'line',
                        label: 'Fitted Trendline',
                        data: reg.trend_points,
                        borderColor: '#8b5cf6',
                        borderWidth: 2.5,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        type: 'line',
                        label: '5-Step Future Forecast',
                        data: reg.forecast_points,
                        borderColor: '#10b981',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        pointRadius: 4,
                        pointBackgroundColor: '#10b981',
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: { display: true, text: reg.feature, color: textColor },
                        grid: { color: gridColor },
                        ticks: { color: textColor }
                    },
                    y: {
                        title: { display: true, text: reg.target, color: textColor },
                        grid: { color: gridColor },
                        ticks: { color: textColor }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: textColor }
                    }
                }
            }
        });
    }

    // ==========================================
    // DATASET COMPARISON ENGINE
    // ==========================================
    elements.btnRunComparison.addEventListener('click', async () => {
        const t1 = elements.compareSelect1.value;
        const t2 = elements.compareSelect2.value;

        if (!t1 || !t2) {
            showToast('Please select two datasets to compare.', true);
            return;
        }

        elements.comparisonResultsContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="text-muted mt-2">Computing schema intersections and distribution variance...</p>
            </div>
        `;

        try {
            const resp = await fetch('/datasets/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table1: t1, table2: t2 })
            });
            const data = await resp.json();
            if (!data.success) {
                elements.comparisonResultsContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }

            const comp = data.comparison;
            const d1 = comp.dataset_1;
            const d2 = comp.dataset_2;
            const sc = comp.schema_comparison;
            const numDiffs = comp.numeric_comparison;

            let html = `
                <!-- Dimension Metrics Matrix -->
                <div class="row g-3 mb-4">
                    <div class="col-6 col-md-3">
                        <div class="comparison-card">
                            <div class="small text-muted text-uppercase fw-semibold mb-1">Rows Comparison</div>
                            <div class="fs-5 fw-bold">${d1.rows.toLocaleString()} vs ${d2.rows.toLocaleString()}</div>
                            <span class="badge ${d2.rows >= d1.rows ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning'} delta-badge mt-1">
                                ${d2.rows >= d1.rows ? '+' : ''}${(d2.rows - d1.rows).toLocaleString()} rows
                            </span>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="comparison-card">
                            <div class="small text-muted text-uppercase fw-semibold mb-1">Columns Width</div>
                            <div class="fs-5 fw-bold">${d1.columns} vs ${d2.columns}</div>
                            <span class="badge bg-primary-subtle text-primary delta-badge mt-1">
                                ${d2.columns - d1.columns >= 0 ? '+' : ''}${d2.columns - d1.columns} cols
                            </span>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="comparison-card">
                            <div class="small text-muted text-uppercase fw-semibold mb-1">Missing Nulls</div>
                            <div class="fs-5 fw-bold">${d1.nulls} vs ${d2.nulls}</div>
                            <span class="badge ${d2.nulls <= d1.nulls ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'} delta-badge mt-1">
                                ${d2.nulls - d1.nulls} null diff
                            </span>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="comparison-card">
                            <div class="small text-muted text-uppercase fw-semibold mb-1">Schema Similarity</div>
                            <div class="fs-5 fw-bold text-primary">${sc.similarity_score}%</div>
                            <span class="badge bg-info-subtle text-info delta-badge mt-1">
                                ${sc.shared_columns_count} shared fields
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Schema Details -->
                <div class="card border mb-4">
                    <div class="card-header bg-transparent fw-bold small text-uppercase text-secondary">
                        <i class="bi bi-diagram-3 me-2"></i>Schema Attributes Comparison
                    </div>
                    <div class="card-body p-3">
                        <div class="mb-2">
                            <strong class="small text-success">Shared Intersecting Columns (${sc.shared_columns.length}):</strong>
                            <div class="d-flex flex-wrap gap-1 mt-1">
                                ${sc.shared_columns.map(c => `<span class="badge bg-success-subtle text-success border border-success-subtle font-monospace">${c}</span>`).join('') || '<span class="text-muted small">None</span>'}
                            </div>
                        </div>
                        <div class="row g-2 mt-2">
                            <div class="col-12 col-md-6">
                                <strong class="small text-primary">Unique to ${d1.name} (${sc.unique_to_1.length}):</strong>
                                <div class="d-flex flex-wrap gap-1 mt-1">
                                    ${sc.unique_to_1.map(c => `<span class="badge bg-primary-subtle text-primary border border-primary-subtle font-monospace">${c}</span>`).join('') || '<span class="text-muted small">None</span>'}
                                </div>
                            </div>
                            <div class="col-12 col-md-6">
                                <strong class="small text-purple">Unique to ${d2.name} (${sc.unique_to_2.length}):</strong>
                                <div class="d-flex flex-wrap gap-1 mt-1">
                                    ${sc.unique_to_2.map(c => `<span class="badge bg-purple-subtle text-purple border border-purple-subtle font-monospace">${c}</span>`).join('') || '<span class="text-muted small">None</span>'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            if (numDiffs.length > 0) {
                html += `
                    <h6 class="fw-bold mb-2 text-secondary"><i class="bi bi-bar-chart-line me-2"></i>Shared Numeric Distribution Variance</h6>
                    <div class="table-responsive border rounded">
                        <table class="table table-sm table-striped align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Column</th>
                                    <th class="text-end">Mean (${d1.name})</th>
                                    <th class="text-end">Mean (${d2.name})</th>
                                    <th class="text-end">Delta Difference</th>
                                    <th class="text-end">% Shift</th>
                                    <th class="text-end">Range (${d1.name})</th>
                                    <th class="text-end">Range (${d2.name})</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                numDiffs.forEach(nd => {
                    const shiftClass = nd.percentage_shift > 0 ? 'text-success' : (nd.percentage_shift < 0 ? 'text-danger' : 'text-muted');
                    html += `
                        <tr>
                            <td class="fw-bold font-monospace text-primary">${nd.column}</td>
                            <td class="text-end">${nd.mean_1.toLocaleString()}</td>
                            <td class="text-end">${nd.mean_2.toLocaleString()}</td>
                            <td class="text-end fw-semibold ${shiftClass}">${nd.delta > 0 ? '+' : ''}${nd.delta}</td>
                            <td class="text-end fw-semibold ${shiftClass}">${nd.percentage_shift > 0 ? '+' : ''}${nd.percentage_shift}%</td>
                            <td class="text-end small text-muted">[${nd.min_1} &rarr; ${nd.max_1}]</td>
                            <td class="text-end small text-muted">[${nd.min_2} &rarr; ${nd.max_2}]</td>
                        </tr>
                    `;
                });
                html += `
                            </tbody>
                        </table>
                    </div>
                `;
            }

            elements.comparisonResultsContainer.innerHTML = html;

        } catch (e) {
            elements.comparisonResultsContainer.innerHTML = `<div class="alert alert-danger">Error: ${e}</div>`;
        }
    });

    // ==========================================
    // INITIAL DASHBOARD ANALYTICS LOADER
    // ==========================================
    async function loadDashboardAnalytics() {
        try {
            const resp = await fetch(`/analytics?table=${encodeURIComponent(state.activeTable)}`);
            const data = await resp.json();
            if (!data.success) return;

            const stats = data.data;

            if (stats.is_students) {
                // Students layout
                document.getElementById('card-label-1').textContent = "Total Students";
                document.getElementById('stat-val-1').textContent = stats.total_students;
                document.getElementById('card-sub-1').innerHTML = '<i class="bi bi-check-circle text-success me-1"></i>Enrolled cohort';

                document.getElementById('card-label-2').textContent = "Departments";
                document.getElementById('stat-val-2').textContent = stats.total_departments;
                document.getElementById('card-sub-2').textContent = "CSE, IT, ECE + 4 more";

                document.getElementById('card-label-3').textContent = "Average CGPA";
                document.getElementById('stat-val-3').textContent = stats.avg_cgpa;
                document.getElementById('card-sub-3').innerHTML = '<i class="bi bi-graph-up text-info me-1"></i>Cohort Mean';

                document.getElementById('card-label-4').textContent = "Highest CGPA";
                document.getElementById('stat-val-4').textContent = stats.max_cgpa;
                document.getElementById('card-sub-4').textContent = "Top Performer";

                document.getElementById('card-label-5').textContent = "Lowest CGPA";
                document.getElementById('stat-val-5').textContent = stats.min_cgpa;
                document.getElementById('card-sub-5').textContent = "Baseline Grade";

                document.getElementById('card-label-6').textContent = "Total Cities";
                document.getElementById('stat-val-6').textContent = stats.total_cities;
                document.getElementById('card-sub-6').textContent = "Tamil Nadu Regions";
            } else {
                // Universal layout for dynamic uploaded tables
                document.getElementById('card-label-1').textContent = "Total Records";
                document.getElementById('stat-val-1').textContent = stats.total_rows.toLocaleString();
                document.getElementById('card-sub-1').innerHTML = `<i class="bi bi-table text-primary me-1"></i>${stats.active_table}`;

                document.getElementById('card-label-2').textContent = "Categories";
                document.getElementById('stat-val-2').textContent = stats.categorical_count;
                document.getElementById('card-sub-2').textContent = "Categorical fields";

                document.getElementById('card-label-3').textContent = "Numeric Fields";
                document.getElementById('stat-val-3').textContent = stats.numeric_count;
                document.getElementById('card-sub-3').textContent = "Continuous metrics";

                document.getElementById('card-label-4').textContent = "Dataset Width";
                document.getElementById('stat-val-4').textContent = stats.total_columns;
                document.getElementById('card-sub-4').textContent = "Features / Cols";

                document.getElementById('card-label-5').textContent = "Missing Cells";
                document.getElementById('stat-val-5').textContent = stats.total_nulls;
                document.getElementById('card-sub-5').textContent = stats.total_nulls === 0 ? "100% Complete" : "Requires attention";

                document.getElementById('card-label-6').textContent = "Duplicates";
                document.getElementById('stat-val-6').textContent = stats.duplicate_count;
                document.getElementById('card-sub-6').textContent = stats.duplicate_count === 0 ? "Pristine integrity" : "Duplicate rows";
            }
        } catch (err) {
            console.error('Failed to load dashboard analytics:', err);
        }
    }

    // ==========================================
    // QUERY EXECUTION (UNIVERSAL & READ-ONLY)
    // ==========================================
    async function executeQuery(queryString) {
        const query = (queryString || elements.queryInput.value).trim();
        if (!query) {
            showToast('Please enter a question to explore the database.', true);
            return;
        }

        // Set Loading State
        elements.btnRunQuery.disabled = true;
        elements.querySpinner.classList.remove('d-none');
        elements.queryBtnIcon.classList.add('d-none');
        elements.unsafeAlert.classList.add('d-none');

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, table: state.activeTable })
            });

            const result = await response.json();

            if (!result.success) {
                // Check if Unsafe Query Blocked
                if (result.unsafe) {
                    elements.unsafeAlertTitle.textContent = 'Unsafe Query Blocked';
                    elements.unsafeAlertMsg.textContent = result.error || 'Destructive query blocked by read-only security policy.';
                    elements.unsafeAlert.classList.remove('d-none');
                    showToast('Security Alert: Unsafe SQL Query Blocked', true);
                } else {
                    showToast(result.error || 'Error processing query', true);
                }
                return;
            }

            // Successfully processed
            state.currentQuery = query;
            state.columns = result.columns || [];
            state.currentData = result.data || [];
            state.filteredData = [...state.currentData];
            state.currentPage = 1;
            state.chartSuggestion = result.chart;

            // Render SQL Verification & Explanation Card
            renderVerification(result);

            // Render Result Table
            renderTable();

            // Render Dynamic Visualizations
            renderChart(result.chart, state.activeChartType);

            // Render AI Insights
            renderInsights(result.insights);

            // Refresh Query History List & User Stats
            loadHistory();
            loadUserStats();

        } catch (error) {
            console.error('Query execution error:', error);
            showToast('Network error while executing query.', true);
        } finally {
            elements.btnRunQuery.disabled = false;
            elements.querySpinner.classList.add('d-none');
            elements.queryBtnIcon.classList.remove('d-none');
        }
    }

    // Form Submit Listener
    elements.queryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        executeQuery();
    });

    // Clear Button Handler
    elements.queryInput.addEventListener('input', () => {
        if (elements.queryInput.value.length > 0) {
            elements.btnClearQuery.classList.remove('d-none');
        } else {
            elements.btnClearQuery.classList.add('d-none');
        }
    });

    elements.btnClearQuery.addEventListener('click', () => {
        elements.queryInput.value = '';
        elements.btnClearQuery.classList.add('d-none');
        elements.queryInput.focus();
    });

    elements.btnCloseUnsafeAlert.addEventListener('click', () => {
        elements.unsafeAlert.classList.add('d-none');
    });

    // Copy SQL Button
    elements.btnCopySql.addEventListener('click', () => {
        const sqlText = elements.verifSqlQuery.textContent;
        navigator.clipboard.writeText(sqlText).then(() => {
            elements.copySqlText.textContent = 'Copied!';
            showToast('SQL query copied to clipboard!');
            setTimeout(() => {
                elements.copySqlText.textContent = 'Copy';
            }, 2000);
        }).catch(err => {
            console.error('Clipboard copy failed:', err);
        });
    });

    // ==========================================
    // RENDER VERIFICATION & EXPLANATION
    // ==========================================
    function renderVerification(data) {
        elements.verifUserQuery.textContent = data.user_query;
        elements.verifSqlQuery.textContent = data.sql_query;
        elements.verifExplanation.textContent = data.explanation;
        elements.badgeLang.textContent = `Language: ${data.language}`;
        elements.badgeTarget.textContent = `Table: ${data.table_name || state.activeTable}`;
        
        // Confidence badge styling
        const conf = data.confidence_score;
        elements.badgeConfidence.textContent = `Confidence: ${conf}%`;
        if (conf >= 90) {
            elements.badgeConfidence.className = 'badge rounded-pill bg-success-subtle text-success border border-success-subtle';
        } else if (conf >= 80) {
            elements.badgeConfidence.className = 'badge rounded-pill bg-info-subtle text-info border border-info-subtle';
        } else {
            elements.badgeConfidence.className = 'badge rounded-pill bg-warning-subtle text-warning border border-warning-subtle';
        }

        // Fuzzy spell check notice
        if (data.corrections && data.corrections.length > 0) {
            const fixList = data.corrections.map(c => `"${c.original}" → "${c.corrected}"`).join(', ');
            elements.verifCorrectedText.textContent = `${data.corrected_query} (${fixList})`;
            elements.verifCorrectionNotice.classList.remove('d-none');
        } else {
            elements.verifCorrectionNotice.classList.add('d-none');
        }

        elements.verifTimestamp.textContent = new Date().toLocaleTimeString();
    }

    // ==========================================
    // RENDER RESULT TABLE WITH PAGINATION & SORT
    // ==========================================
    function renderTable() {
        const total = state.filteredData.length;
        elements.rowCountBadge.textContent = `${total} Record${total === 1 ? '' : 's'}`;

        if (total === 0) {
            elements.tableHead.innerHTML = '';
            elements.tableBody.innerHTML = '';
            elements.tableEmpty.classList.remove('d-none');
            elements.paginationInfo.textContent = 'Showing 0 records';
            elements.tablePagination.innerHTML = '';
            return;
        }

        elements.tableEmpty.classList.add('d-none');

        // Render Table Header with Sort Indicators
        let headHtml = '<tr>';
        state.columns.forEach(col => {
            let sortIcon = 'bi-arrow-down-up text-muted opacity-50';
            if (state.sortColumn === col) {
                sortIcon = state.sortDirection === 'asc' ? 'bi-sort-up text-primary' : 'bi-sort-down text-primary';
            }
            headHtml += `
                <th data-column="${col}">
                    <div class="d-flex align-items-center justify-content-between">
                        <span>${col.replace('_', ' ').toUpperCase()}</span>
                        <i class="bi ${sortIcon} ms-1"></i>
                    </div>
                </th>
            `;
        });
        headHtml += '</tr>';
        elements.tableHead.innerHTML = headHtml;

        // Table Header Click Sort Listener
        elements.tableHead.querySelectorAll('th').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.getAttribute('data-column');
                if (state.sortColumn === col) {
                    state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortColumn = col;
                    state.sortDirection = 'asc';
                }
                sortTableData();
                renderTable();
            });
        });

        // Pagination calculations
        const startIdx = (state.currentPage - 1) * state.pageSize;
        const endIdx = Math.min(startIdx + state.pageSize, total);
        const pageData = state.filteredData.slice(startIdx, endIdx);

        // Render Rows
        let bodyHtml = '';
        pageData.forEach(row => {
            bodyHtml += '<tr>';
            state.columns.forEach(col => {
                const val = row[col];
                let displayVal = val !== null && val !== undefined ? val : '-';
                
                // Highlight CGPA values
                if (col === 'cgpa' && typeof val === 'number') {
                    const badgeClass = val >= 9.0 ? 'bg-success-subtle text-success' : (val >= 8.0 ? 'bg-primary-subtle text-primary' : 'bg-secondary-subtle text-body');
                    displayVal = `<span class="badge ${badgeClass} rounded-pill px-2 py-1">${val.toFixed(2)}</span>`;
                }
                bodyHtml += `<td>${displayVal}</td>`;
            });
            bodyHtml += '</tr>';
        });
        elements.tableBody.innerHTML = bodyHtml;

        elements.paginationInfo.textContent = `Showing ${startIdx + 1} to ${endIdx} of ${total} records`;
        renderPaginationButtons(total);
    }

    function sortTableData() {
        if (!state.sortColumn) return;
        const col = state.sortColumn;
        const dir = state.sortDirection === 'asc' ? 1 : -1;

        state.filteredData.sort((a, b) => {
            const valA = a[col];
            const valB = b[col];
            if (valA === valB) return 0;
            if (valA === null || valA === undefined) return 1;
            if (valB === null || valB === undefined) return -1;
            if (typeof valA === 'number' && typeof valB === 'number') {
                return (valA - valB) * dir;
            }
            return String(valA).localeCompare(String(valB)) * dir;
        });
    }

    function renderPaginationButtons(totalRecords) {
        const totalPages = Math.ceil(totalRecords / state.pageSize) || 1;
        let html = '';

        html += `
            <li class="page-item ${state.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${state.currentPage - 1}" aria-label="Previous">
                    <span aria-hidden="true">&laquo;</span>
                </a>
            </li>
        `;

        const maxPagesToShow = 5;
        let startPage = Math.max(1, state.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
        if (endPage - startPage < maxPagesToShow - 1) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }

        for (let p = startPage; p <= endPage; p++) {
            html += `
                <li class="page-item ${p === state.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${p}">${p}</a>
                </li>
            `;
        }

        html += `
            <li class="page-item ${state.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${state.currentPage + 1}" aria-label="Next">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        `;

        elements.tablePagination.innerHTML = html;

        elements.tablePagination.querySelectorAll('a.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = parseInt(link.getAttribute('data-page'), 10);
                if (targetPage >= 1 && targetPage <= totalPages && targetPage !== state.currentPage) {
                    state.currentPage = targetPage;
                    renderTable();
                }
            });
        });
    }

    elements.pageSizeSelect.addEventListener('change', (e) => {
        state.pageSize = parseInt(e.target.value, 10);
        state.currentPage = 1;
        renderTable();
    });

    elements.tableFilterInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) {
            state.filteredData = [...state.currentData];
        } else {
            state.filteredData = state.currentData.filter(row => {
                return Object.values(row).some(val => 
                    String(val).toLowerCase().includes(query)
                );
            });
        }
        state.currentPage = 1;
        renderTable();
    });

    // ==========================================
    // CHART.JS VISUALIZATION ENGINE
    // ==========================================
    function renderChart(chartData, requestedType = 'auto') {
        if (!chartData || !chartData.labels || chartData.labels.length === 0) {
            return;
        }

        const isDark = state.theme === 'dark';
        const textColor = isDark ? '#cbd5e1' : '#475569';
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';

        let chartType = requestedType === 'auto' ? (chartData.type || 'bar') : requestedType;
        elements.chartCardTitle.textContent = chartData.title || 'Data Visualization';

        const modernColors = [
            'rgba(59, 130, 246, 0.85)',
            'rgba(139, 92, 246, 0.85)',
            'rgba(20, 184, 166, 0.85)',
            'rgba(245, 158, 11, 0.85)',
            'rgba(244, 63, 94, 0.85)',
            'rgba(99, 102, 241, 0.85)',
            'rgba(16, 185, 129, 0.85)',
            'rgba(236, 72, 153, 0.85)',
            'rgba(14, 165, 233, 0.85)'
        ];

        const modernBorders = modernColors.map(c => c.replace('0.85', '1.0'));

        const datasetBackground = (chartType === 'pie' || chartType === 'doughnut')
            ? modernColors.slice(0, chartData.labels.length)
            : 'rgba(59, 130, 246, 0.85)';

        const datasetBorder = (chartType === 'pie' || chartType === 'doughnut')
            ? modernBorders.slice(0, chartData.labels.length)
            : '#2563eb';

        if (state.chartInstance) {
            state.chartInstance.destroy();
        }

        const ctx = elements.chartCanvas.getContext('2d');
        state.chartInstance = new Chart(ctx, {
            type: chartType,
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: chartData.title || 'Metrics',
                    data: chartData.data,
                    backgroundColor: datasetBackground,
                    borderColor: datasetBorder,
                    borderWidth: 1.5,
                    borderRadius: chartType === 'bar' ? 6 : 0,
                    tension: 0.35,
                    fill: chartType === 'line'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: (chartType === 'pie' || chartType === 'doughnut'),
                        position: 'bottom',
                        labels: {
                            color: textColor,
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }
                        }
                    },
                    tooltip: {
                        backgroundColor: isDark ? '#1e293b' : '#0f172a',
                        titleColor: '#ffffff',
                        bodyColor: '#93c5fd',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 8
                    }
                },
                scales: (chartType === 'pie' || chartType === 'doughnut') ? {} : {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { color: textColor, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    }
                }
            }
        });
    }

    elements.chartTypeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.chartTypeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const type = btn.getAttribute('data-type');
            state.activeChartType = type;
            if (state.chartSuggestion) {
                renderChart(state.chartSuggestion, type);
            }
        });
    });

    elements.btnDownloadChart.addEventListener('click', () => {
        if (!state.chartInstance) return;
        const link = document.createElement('a');
        link.download = `NLDE_Chart_${Date.now()}.png`;
        link.href = elements.chartCanvas.toDataURL('image/png');
        link.click();
        showToast('Chart image downloaded successfully.');
    });

    // ==========================================
    // RENDER AI INSIGHTS
    // ==========================================
    function renderInsights(insights) {
        if (!insights || insights.length === 0) {
            elements.insightsList.innerHTML = '<li class="text-muted small">No dynamic insights available.</li>';
            return;
        }

        let html = '';
        insights.forEach(item => {
            html += `
                <li class="insight-item">
                    <i class="bi bi-lightbulb-fill text-warning me-2 fs-6"></i>
                    <span>${item}</span>
                </li>
            `;
        });
        elements.insightsList.innerHTML = html;
    }

    // ==========================================
    // QUERY HISTORY OFF-CANVAS
    // ==========================================
    async function loadHistory() {
        try {
            const resp = await fetch('/history');
            const data = await resp.json();
            if (!data.success) return;

            const history = data.history || [];
            elements.historyBadgeCount.textContent = history.length;

            if (history.length === 0) {
                elements.historyList.innerHTML = '';
                elements.historyEmpty.classList.remove('d-none');
                return;
            }

            elements.historyEmpty.classList.add('d-none');
            let html = '';
            history.forEach(item => {
                html += `
                    <div class="history-item-card p-2 border rounded-3 mb-2" data-query="${encodeURIComponent(item.query)}" data-table="${item.table || 'students'}">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="fw-bold small text-primary text-truncate" style="max-width: 170px;">${item.query}</span>
                            <div class="d-flex align-items-center gap-1">
                                <span class="badge bg-secondary-subtle text-body-secondary rounded-pill">${item.timestamp ? String(item.timestamp).substring(11, 19) : ''}</span>
                                <button type="button" class="btn btn-outline-danger btn-sm p-0 px-1 border-0 del-history-btn" data-id="${item.id}" title="Delete query from history">
                                    <i class="bi bi-x-circle"></i>
                                </button>
                            </div>
                        </div>
                        <div class="small text-muted font-monospace text-truncate mb-2">${item.sql}</div>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="small text-muted"><span class="badge bg-info-subtle text-info me-1">${item.table || 'students'}</span>${item.row_count} rows</span>
                            <button type="button" class="btn btn-sm btn-outline-primary py-0 px-2 rounded-pill run-again-btn">
                                <i class="bi bi-arrow-repeat me-1"></i>Run
                            </button>
                        </div>
                    </div>
                `;
            });
            elements.historyList.innerHTML = html;

            // Bind card click to run query
            elements.historyList.querySelectorAll('.run-again-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const card = btn.closest('.history-item-card');
                    const q = decodeURIComponent(card.getAttribute('data-query'));
                    const tbl = card.getAttribute('data-table');
                    if (tbl && tbl !== state.activeTable) {
                        switchActiveDataset(tbl);
                    }
                    elements.queryInput.value = q;
                    elements.btnClearQuery.classList.remove('d-none');
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(elements.historyOffcanvas);
                    if (bsOffcanvas) bsOffcanvas.hide();
                    executeQuery(q);
                });
            });

            // Bind card click
            elements.historyList.querySelectorAll('.history-item-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    if (e.target.closest('.del-history-btn') || e.target.closest('.run-again-btn')) return;
                    const q = decodeURIComponent(card.getAttribute('data-query'));
                    const tbl = card.getAttribute('data-table');
                    if (tbl && tbl !== state.activeTable) {
                        switchActiveDataset(tbl);
                    }
                    elements.queryInput.value = q;
                    elements.btnClearQuery.classList.remove('d-none');
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(elements.historyOffcanvas);
                    if (bsOffcanvas) bsOffcanvas.hide();
                    executeQuery(q);
                });
            });

            // Bind delete item button
            elements.historyList.querySelectorAll('.del-history-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const id = btn.getAttribute('data-id');
                    try {
                        const res = await fetch(`/history/${id}`, { method: 'DELETE' });
                        const json = await res.json();
                        if (json.success) {
                            loadHistory();
                            loadUserStats();
                        }
                    } catch (err) {
                        console.error(err);
                    }
                });
            });

        } catch (err) {
            console.error('Failed to load query history:', err);
        }
    }

    // Clear All History Button
    const btnClearAllHistory = document.getElementById('btn-clear-all-history');
    if (btnClearAllHistory) {
        btnClearAllHistory.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to clear your entire query history?')) return;
            try {
                const res = await fetch('/history', { method: 'DELETE' });
                const json = await res.json();
                if (json.success) {
                    showToast('Query history cleared.');
                    loadHistory();
                    loadUserStats();
                }
            } catch (err) {
                console.error(err);
            }
        });
    }

    // User Dashboard KPIs
    async function loadUserStats() {
        try {
            const resp = await fetch('/api/user/stats');
            const data = await resp.json();
            if (data.success && data.stats) {
                const s = data.stats;
                const dsEl = document.getElementById('user-stat-datasets');
                const repEl = document.getElementById('user-stat-reports');
                const qEl = document.getElementById('user-stat-queries');
                const lastLoginEl = document.getElementById('user-last-login-text');
                
                if (dsEl) dsEl.textContent = s.dataset_count || 0;
                if (repEl) repEl.textContent = s.report_count || 0;
                if (qEl) qEl.textContent = s.history_count || 0;
                if (lastLoginEl && s.last_login) lastLoginEl.textContent = s.last_login;
            }
        } catch (err) {
            console.error('Failed to load user stats:', err);
        }
    }

    // ==========================================
    // DATABASE SCHEMA MODAL
    // ==========================================
    elements.schemaModal.addEventListener('show.bs.modal', async () => {
        elements.schemaModalContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="text-muted mt-2">Loading database schema...</p>
            </div>
        `;

        try {
            const resp = await fetch('/schema');
            const data = await resp.json();
            if (!data.success) {
                elements.schemaModalContent.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                return;
            }

            const tables = data.schema.tables;
            let html = '';
            tables.forEach(t => {
                html += `
                    <div class="mb-4">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="fw-bold mb-0 text-primary"><i class="bi bi-table me-2"></i>Table: ${t.table_name}</h6>
                            <span class="badge bg-primary-subtle text-primary">${t.row_count} Records (${t.column_count} Columns)</span>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm table-bordered">
                                <thead class="table-light">
                                    <tr>
                                        <th>#</th>
                                        <th>Column Name</th>
                                        <th>Data Type</th>
                                        <th>Primary Key</th>
                                        <th>Not Null</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                t.columns.forEach((col, idx) => {
                    html += `
                        <tr>
                            <td>${idx + 1}</td>
                            <td class="fw-semibold">${col.name}</td>
                            <td><span class="badge bg-secondary-subtle text-body font-monospace">${col.type}</span></td>
                            <td>${col.pk ? '<i class="bi bi-key-fill text-warning"></i> PK' : '-'}</td>
                            <td>${col.notnull ? '<i class="bi bi-check-circle-fill text-success"></i>' : '-'}</td>
                        </tr>
                    `;
                });
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });
            elements.schemaModalContent.innerHTML = html;
        } catch (err) {
            elements.schemaModalContent.innerHTML = `<div class="alert alert-danger">Failed to load schema: ${err}</div>`;
        }
    });

    // ==========================================
    // DATA QUALITY MODAL
    // ==========================================
    elements.qualityModal.addEventListener('show.bs.modal', async () => {
        elements.qualityModalContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-success" role="status"></div>
                <p class="text-muted mt-2">Auditing data health...</p>
            </div>
        `;

        try {
            const resp = await fetch('/quality');
            const data = await resp.json();
            if (!data.success) {
                elements.qualityModalContent.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                return;
            }

            const q = data.quality;
            const healthColor = q.health_score >= 95 ? 'success' : (q.health_score >= 80 ? 'warning' : 'danger');

            let html = `
                <div class="text-center p-3 mb-4 rounded bg-body-tertiary">
                    <div class="display-5 fw-bold text-${healthColor}">${q.health_score}%</div>
                    <div class="text-muted small text-uppercase fw-semibold mt-1">Data Health Score (${q.summary_status})</div>
                    <div class="progress mt-3" style="height: 10px;">
                        <div class="progress-bar bg-${healthColor}" role="progressbar" style="width: ${q.health_score}%"></div>
                    </div>
                </div>

                <h6 class="fw-bold mb-3">Integrity Audit Breakdown</h6>
                <div class="row g-3">
                    <div class="col-6 col-md-3">
                        <div class="p-3 border rounded text-center">
                            <div class="fs-4 fw-bold">${q.total_records}</div>
                            <div class="small text-muted">Total Records</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-3 border rounded text-center">
                            <div class="fs-4 fw-bold ${q.total_nulls > 0 ? 'text-danger' : 'text-success'}">${q.total_nulls}</div>
                            <div class="small text-muted">Missing/Nulls</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-3 border rounded text-center">
                            <div class="fs-4 fw-bold ${q.duplicate_records > 0 ? 'text-danger' : 'text-success'}">${q.duplicate_records}</div>
                            <div class="small text-muted">Duplicates</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-3 border rounded text-center">
                            <div class="fs-4 fw-bold ${q.invalid_cgpa > 0 ? 'text-danger' : 'text-success'}">${q.invalid_cgpa}</div>
                            <div class="small text-muted">Invalid CGPA</div>
                        </div>
                    </div>
                </div>

                <div class="mt-4">
                    <h6 class="fw-bold mb-2">Column-Level Completeness</h6>
                    <ul class="list-group list-group-flush border rounded">
            `;

            for (const [col, count] of Object.entries(q.missing_values)) {
                html += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <span class="font-monospace">${col}</span>
                        <span class="badge ${count === 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'} rounded-pill">
                            ${count === 0 ? '100% Complete' : `${count} Missing`}
                        </span>
                    </li>
                `;
            }

            html += `
                    </ul>
                </div>
            `;

            elements.qualityModalContent.innerHTML = html;
        } catch (err) {
            elements.qualityModalContent.innerHTML = `<div class="alert alert-danger">Failed to run data quality audit: ${err}</div>`;
        }
    });

    // ==========================================
    // INITIALIZATION RUNNER
    // ==========================================
    loadDatasetsList();
    loadDashboardAnalytics();
    loadHistory();
    loadUserStats();

    // Default query on initial load: "Show all students"
    executeQuery("Show all students");
});
