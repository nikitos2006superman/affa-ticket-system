// AJAX-проверка билета: после успешной отметки поле очищается,
// чтобы можно было сразу сканировать следующий билет.

(function () {
    const form = document.getElementById('check-in-form');
    const input = document.getElementById('ticket_code');
    const resultBox = document.getElementById('check-in-result');
    if (!form || !input || !resultBox) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const code = input.value.trim();
        if (!code) return;

        try {
            const r = await fetch('/admin/api/check-in', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code }),
            });
            const data = await r.json();

            if (data.ok) {
                resultBox.innerHTML =
                    '<div class="result-success">' +
                    '<h3>✓ Билет принят</h3>' +
                    '<div><strong>Мероприятие:</strong> ' + escapeHtml(data.event_title) + '</div>' +
                    '<div><strong>Владелец:</strong> ' + escapeHtml(data.holder_name) + '</div>' +
                    '<div><strong>Время отметки:</strong> ' + new Date(data.checked_at).toLocaleTimeString() + '</div>' +
                    '</div>';
                input.value = '';
                input.focus();
            } else {
                resultBox.innerHTML =
                    '<div class="result-error">' +
                    '<h3>✗ Ошибка</h3>' +
                    '<div>' + escapeHtml(data.error || 'Неизвестная ошибка') + '</div>' +
                    '</div>';
                input.select();
            }
        } catch (err) {
            resultBox.innerHTML =
                '<div class="result-error"><h3>✗ Ошибка сети</h3><div>' + escapeHtml(err.message) + '</div></div>';
        }
    });

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
        });
    }
})();
