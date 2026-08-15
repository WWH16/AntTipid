// Shared "Edit Transaction" sheet controller.
// Bottom sheet on mobile, centered modal on desktop. Used by both the
// transactions list ("All Activity" tab) and the receipt detail page -
// include dashboard/components/edit_transaction_sheet.html once per page,
// then call window.initEditTransactionSheet() to get an { open, close } API.
(function () {
    function initEditTransactionSheet() {
        const wrapper = document.getElementById('edit-sheet-wrapper');
        if (!wrapper) return null;

        const backdrop = document.getElementById('edit-sheet-backdrop');
        const content = document.getElementById('edit-sheet-content');
        const dragHandle = document.getElementById('edit-sheet-handle');
        const typeIcon = document.getElementById('edit-sheet-type-icon');
        const titleEl = document.getElementById('edit-sheet-title');

        const inputAmount = document.getElementById('edit-input-amount');
        const inputTitle = document.getElementById('edit-input-title');
        const inputDate = document.getElementById('edit-input-date');
        const selectAccount = document.getElementById('edit-select-account');
        const inputNotes = document.getElementById('edit-input-notes');
        const categoryBtns = document.querySelectorAll('.edit-category-btn');
        const presetChips = document.querySelectorAll('.edit-preset-chip');

        const cancelBtn = document.getElementById('btn-cancel-edit-sheet');
        const saveBtn = document.getElementById('btn-save-edit-sheet');

        const toast = document.getElementById('edit-toast-success');
        const toastMsgEl = document.getElementById('edit-toast-msg');

        const TYPE_DISPLAY = {
            expense: { label: 'Edit Expense', icon: 'arrow_downward', colorClass: 'text-expense' },
            income: { label: 'Edit Income', icon: 'arrow_upward', colorClass: 'text-primary' },
            transfer: { label: 'Edit Transfer', icon: 'swap_horiz', colorClass: 'text-amber-700' },
        };

        function setType(type) {
            const display = TYPE_DISPLAY[type] || TYPE_DISPLAY.expense;
            if (titleEl) titleEl.textContent = display.label;
            if (typeIcon) {
                typeIcon.textContent = display.icon;
                typeIcon.classList.remove('text-expense', 'text-primary', 'text-amber-700');
                typeIcon.classList.add(display.colorClass);
            }
        }

        function setCategory(category) {
            categoryBtns.forEach(b => {
                b.classList.remove('border-primary', 'bg-primary/10', 'text-primary', 'shadow-xs');
                b.classList.add('border-surface-variant/60', 'bg-surface-container-low/40', 'text-on-surface-variant');

                const labelSpan = b.querySelector('span:last-child');
                if (labelSpan) {
                    labelSpan.classList.remove('font-semibold');
                    labelSpan.classList.add('font-medium');
                }
                const iconBox = b.querySelector('.w-9');
                if (iconBox) {
                    iconBox.classList.remove('bg-primary/20', 'text-primary');
                    iconBox.classList.add('bg-surface-container', 'text-on-surface-variant');
                }
                const iconEl = b.querySelector('.material-symbols-outlined');
                if (iconEl) iconEl.style.fontVariationSettings = "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24";
            });

            const activeBtn = document.querySelector(`.edit-category-btn[data-category="${category}"]`);
            if (!activeBtn) return;

            activeBtn.classList.add('border-primary', 'bg-primary/10', 'text-primary', 'shadow-xs');
            activeBtn.classList.remove('border-surface-variant/60', 'bg-surface-container-low/40', 'text-on-surface-variant');

            const activeLabel = activeBtn.querySelector('span:last-child');
            if (activeLabel) {
                activeLabel.classList.remove('font-medium');
                activeLabel.classList.add('font-semibold');
            }
            const activeIconBox = activeBtn.querySelector('.w-9');
            if (activeIconBox) {
                activeIconBox.classList.remove('bg-surface-container', 'text-on-surface-variant');
                activeIconBox.classList.add('bg-primary/20', 'text-primary');
            }
            const activeIconEl = activeBtn.querySelector('.material-symbols-outlined');
            if (activeIconEl) activeIconEl.style.fontVariationSettings = "'FILL' 1, 'wght' 300, 'GRAD' 0, 'opsz' 24";
        }

        categoryBtns.forEach(btn => btn.addEventListener('click', () => setCategory(btn.dataset.category)));

        presetChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const addVal = parseFloat(chip.dataset.add) || 0;
                const currentVal = parseFloat(inputAmount.value) || 0;
                inputAmount.value = (currentVal + addVal).toFixed(2);
                inputAmount.focus();
            });
        });

        let hideTimer = null;

        function open(data) {
            data = data || {};
            if (hideTimer) {
                clearTimeout(hideTimer);
                hideTimer = null;
            }
            content.style.transition = '';
            content.style.transform = '';

            if (inputAmount) inputAmount.value = data.editAmount ? parseFloat(data.editAmount).toFixed(2) : '';
            if (inputTitle) inputTitle.value = data.editTitle || '';
            if (inputDate) inputDate.value = data.editDate || '';
            if (selectAccount && data.editAccount) selectAccount.value = data.editAccount;
            if (inputNotes) inputNotes.value = data.editNotes || '';
            setType(data.editType || 'expense');
            setCategory(data.editCategory || '');

            document.body.style.overflow = 'hidden';
            wrapper.classList.remove('hidden');
            requestAnimationFrame(() => {
                backdrop.classList.remove('opacity-0');
                backdrop.classList.add('opacity-100');
                content.classList.remove('translate-y-full', 'sm:scale-95', 'opacity-0');
                content.classList.add('translate-y-0', 'sm:scale-100', 'opacity-100');
            });
        }

        function close() {
            if (hideTimer) clearTimeout(hideTimer);
            backdrop.classList.remove('opacity-100');
            backdrop.classList.add('opacity-0');
            content.classList.remove('translate-y-0', 'sm:scale-100', 'opacity-100');
            content.classList.add('translate-y-full', 'sm:scale-95', 'opacity-0');
            hideTimer = setTimeout(() => {
                wrapper.classList.add('hidden');
                document.body.style.overflow = '';
                content.style.transition = '';
                content.style.transform = '';
                hideTimer = null;
            }, 200);
        }

        function showToast(message) {
            if (!toast) return;
            if (toastMsgEl && message) toastMsgEl.textContent = message;
            setTimeout(() => {
                toast.classList.remove('hidden');
                requestAnimationFrame(() => {
                    toast.classList.remove('opacity-0');
                    toast.classList.add('opacity-100');
                });
                setTimeout(() => {
                    toast.classList.remove('opacity-100');
                    toast.classList.add('opacity-0');
                    setTimeout(() => toast.classList.add('hidden'), 300);
                }, 1600);
            }, 220);
        }

        if (cancelBtn) cancelBtn.addEventListener('click', close);
        if (backdrop) backdrop.addEventListener('click', close);

        let onSaveCallback = null;

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                close();
                if (onSaveCallback) onSaveCallback();
                showToast();
            });
        }

        // Drag Down to Dismiss Gesture (mobile)
        let startY = 0;
        let currentY = 0;
        let isDragging = false;

        if (dragHandle) {
            dragHandle.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
                currentY = startY;
                isDragging = true;
                content.style.transition = 'none';
            }, { passive: true });

            window.addEventListener('touchmove', (e) => {
                if (!isDragging) return;
                currentY = e.touches[0].clientY;
                const deltaY = currentY - startY;
                if (deltaY > 0) content.style.transform = `translateY(${deltaY}px)`;
            }, { passive: true });

            window.addEventListener('touchend', () => {
                if (!isDragging) return;
                isDragging = false;
                content.style.transition = '';
                const deltaY = currentY - startY;
                if (deltaY > 80) {
                    close();
                } else {
                    content.style.transform = '';
                }
            });
        }

        return {
            open,
            close,
            showToast,
            setOnSave(callback) { onSaveCallback = callback; },
        };
    }

    window.initEditTransactionSheet = initEditTransactionSheet;
})();
