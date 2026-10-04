/**
 * AntTipid shared UI helpers, loaded on every app page from base.html.
 *
 *   antToast(message, { type, action, duration })   non-blocking notice; replaces alert()
 *   antDeferred({ message, commit, undo, delay })   "Deleted · Undo" pattern
 *   antFocusTrap(container)                         traps Tab inside a dialog; returns release()
 *   antEscape(value)                                HTML-escapes text for template strings
 */
(function () {
    'use strict';

    function antEscape(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ─── Toasts ───────────────────────────────────────────────────────────
    let region = null;

    function getRegion() {
        if (region && document.body.contains(region)) return region;
        region = document.createElement('div');
        region.id = 'ant-toast-region';
        region.className = 'ant-toast-region';
        region.setAttribute('role', 'status');
        region.setAttribute('aria-live', 'polite');
        document.body.appendChild(region);
        return region;
    }

    const TOAST_ICONS = { success: 'check_circle', error: 'error', info: 'info' };

    function antToast(message, options) {
        const opts = options || {};
        const type = opts.type || 'info';
        const duration = opts.duration != null ? opts.duration : (type === 'error' ? 7000 : 4000);

        const toast = document.createElement('div');
        toast.className = 'ant-toast ant-toast--' + type;
        if (type === 'error') toast.setAttribute('role', 'alert');

        const icon = document.createElement('span');
        icon.className = 'material-symbols-outlined ant-toast__icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = TOAST_ICONS[type] || TOAST_ICONS.info;
        toast.appendChild(icon);

        const text = document.createElement('p');
        text.className = 'ant-toast__text';
        text.textContent = message;
        toast.appendChild(text);

        let timer = null;
        function dismiss() {
            clearTimeout(timer);
            toast.classList.remove('is-visible');
            setTimeout(() => toast.remove(), 200);
        }

        if (opts.action && opts.action.label) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'ant-toast__action';
            btn.textContent = opts.action.label;
            btn.addEventListener('click', () => {
                dismiss();
                if (typeof opts.action.onClick === 'function') opts.action.onClick();
            });
            toast.appendChild(btn);
        }

        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'ant-toast__close';
        close.setAttribute('aria-label', 'Dismiss');
        close.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">close</span>';
        close.addEventListener('click', dismiss);
        toast.appendChild(close);

        getRegion().appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('is-visible'));
        if (duration > 0) timer = setTimeout(dismiss, duration);

        return { dismiss: dismiss, element: toast };
    }

    // Toasts queued before a redirect: sessionStorage survives the navigation.
    function antToastAfterRedirect(message, options) {
        try {
            sessionStorage.setItem('ant-pending-toast', JSON.stringify({ message: message, options: options || {} }));
        } catch (e) { /* storage blocked: skip */ }
    }

    function flushPendingToast() {
        try {
            const raw = sessionStorage.getItem('ant-pending-toast');
            if (!raw) return;
            sessionStorage.removeItem('ant-pending-toast');
            const data = JSON.parse(raw);
            if (data && data.message) antToast(data.message, data.options);
        } catch (e) { /* ignore */ }
    }

    // ─── Deferred commit with Undo ────────────────────────────────────────
    const pending = new Set();

    function antDeferred(options) {
        const opts = options || {};
        const delay = opts.delay || 5000;
        let done = false;

        const entry = {
            commit: function () {
                if (done) return;
                done = true;
                pending.delete(entry);
                clearTimeout(timer);
                return opts.commit && opts.commit({ keepalive: true });
            }
        };

        const timer = setTimeout(() => {
            if (done) return;
            done = true;
            pending.delete(entry);
            Promise.resolve(opts.commit && opts.commit({ keepalive: false })).catch(() => {
                if (typeof opts.undo === 'function') opts.undo();
                antToast(opts.errorMessage || 'Could not delete. Your item was restored.', { type: 'error' });
            });
        }, delay);

        pending.add(entry);

        antToast(opts.message || 'Deleted', {
            type: 'success',
            duration: delay,
            action: {
                label: 'Undo',
                onClick: function () {
                    if (done) return;
                    done = true;
                    clearTimeout(timer);
                    pending.delete(entry);
                    if (typeof opts.undo === 'function') opts.undo();
                }
            }
        });
    }

    // Leaving the page commits anything still waiting (fetch keepalive survives unload).
    window.addEventListener('pagehide', () => {
        pending.forEach((entry) => entry.commit());
    });

    // ─── Focus trap for dialogs ───────────────────────────────────────────
    const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function antFocusTrap(container, initialFocus) {
        if (!container) return function () {};
        const previouslyFocused = document.activeElement;

        function visibleFocusable() {
            return Array.from(container.querySelectorAll(FOCUSABLE)).filter((el) => el.offsetParent !== null || el === document.activeElement);
        }

        function onKeydown(e) {
            if (e.key !== 'Tab') return;
            const items = visibleFocusable();
            if (!items.length) { e.preventDefault(); return; }
            const first = items[0];
            const last = items[items.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }

        container.addEventListener('keydown', onKeydown);
        requestAnimationFrame(() => {
            const target = (typeof initialFocus === 'string' ? container.querySelector(initialFocus) : initialFocus) || visibleFocusable()[0];
            if (target) target.focus({ preventScroll: true });
        });

        return function release() {
            container.removeEventListener('keydown', onKeydown);
            if (previouslyFocused && typeof previouslyFocused.focus === 'function' && document.body.contains(previouslyFocused)) {
                previouslyFocused.focus({ preventScroll: true });
            }
        };
    }

    window.antEscape = antEscape;
    window.antToast = antToast;
    window.antToastAfterRedirect = antToastAfterRedirect;
    window.antDeferred = antDeferred;
    window.antFocusTrap = antFocusTrap;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', flushPendingToast);
    } else {
        flushPendingToast();
    }
})();
