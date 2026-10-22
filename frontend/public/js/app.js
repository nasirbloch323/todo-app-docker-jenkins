(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  // ---- Mobile menu ----
  var menuBtn = $('#menu-btn'), links = $('#links');
  menuBtn.addEventListener('click', function () {
    var open = links.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', String(open));
  });
  links.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') { links.classList.remove('open'); menuBtn.setAttribute('aria-expanded', 'false'); }
  });

  // ---- Portal status (the three tiers) ----
  function setTier(name, state) {
    var li = $('.chips [data-tier="' + name + '"]');
    li.className = state;
    li.title = name + ': ' + state;
  }
  function checkStatus() {
    fetch('/api/health', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        setTier('frontend', 'ok'); setTier('backend', 'ok');
        setTier('database', d.database === 'up' ? 'ok' : 'bad');
        $('#version').textContent = '#' + d.version;
      })
      .catch(function () {
        setTier('frontend', 'ok'); setTier('backend', 'bad'); setTier('database', 'unknown');
      });
  }

  // ---- Notices ----
  var LABELS = { alert: 'Alert', advisory: 'Advisory', vaccination: 'Vaccination', camp: 'Camp' };
  function loadNotices() {
    var box = $('#notice-list');
    fetch('/api/notices')
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (items) {
        box.textContent = '';
        items.forEach(function (n) {
          var card = el('article', 'notice ' + n.category);
          var head = el('div', 'notice-head');
          head.appendChild(el('span', 'badge', LABELS[n.category] || n.category));
          var d = new Date(n.published_at);
          if (!isNaN(d)) head.appendChild(el('time', 'muted small', d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })));
          card.appendChild(head);
          card.appendChild(el('h3', '', n.title));
          card.appendChild(el('p', '', n.body));
          box.appendChild(card);
        });
      })
      .catch(function () {
        box.textContent = '';
        box.appendChild(el('p', 'muted', 'Notices could not be loaded right now. Please refresh in a moment.'));
      });
  }

  // ---- Departments (grid and booking dropdown) ----
  function loadDepartments() {
    var box = $('#dept-list'), select = $('#department');
    fetch('/api/departments')
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (items) {
        box.textContent = '';
        select.textContent = '';
        var first = el('option', '', 'Choose a department');
        first.value = '';
        select.appendChild(first);
        items.forEach(function (dpt) {
          var card = el('article', 'dept');
          card.appendChild(el('h3', '', dpt.name));
          card.appendChild(el('p', '', dpt.description));
          card.appendChild(el('p', 'hours', dpt.opd_hours));
          var b = el('button', 'link-btn', 'Book here');
          b.type = 'button';
          b.addEventListener('click', function () {
            select.value = dpt.slug;
            $('#appointments').scrollIntoView({ behavior: 'smooth' });
            $('#name').focus({ preventScroll: true });
          });
          card.appendChild(b);
          box.appendChild(card);

          var o = el('option', '', dpt.name);
          o.value = dpt.slug;
          select.appendChild(o);
        });
      })
      .catch(function () {
        box.textContent = '';
        box.appendChild(el('p', 'muted', 'Departments could not be loaded right now. Please refresh in a moment.'));
        select.textContent = '';
        var o = el('option', '', 'Unavailable'); o.value = '';
        select.appendChild(o);
      });
  }

  function loadStats() {
    fetch('/api/stats')
      .then(function (r) { return r.json(); })
      .then(function (d) { $('#stat-dept').textContent = d.departments; $('#stat-appt').textContent = d.appointments; })
      .catch(function () {});
  }

  // ---- Booking ----
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDate(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  var dateInput = $('#date'), today = new Date(), max = new Date();
  max.setDate(max.getDate() + 60);
  dateInput.min = isoDate(today);
  dateInput.max = isoDate(max);

  var bookForm = $('#book-form'), bookMsg = $('#book-msg'), bookBtn = $('#book-btn');

  function show(msgEl, text, kind) { msgEl.textContent = text; msgEl.className = 'form-msg ' + (kind || ''); }

  bookForm.addEventListener('submit', function (e) {
    e.preventDefault();
    document.querySelectorAll('.field-error').forEach(function (p) { p.textContent = ''; });
    show(bookMsg, '');
    bookBtn.disabled = true;

    fetch('/api/appointments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: bookForm.elements['name'].value, phone: bookForm.elements['phone'].value,
        department: bookForm.elements['department'].value, date: bookForm.elements['date'].value, note: bookForm.elements['note'].value
      })
    })
      .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, body: body }; }); })
      .then(function (r) {
        if (r.ok) {
          bookForm.reset();
          show(bookMsg, 'Booked. Your reference number is ' + r.body.reference + '. Keep it to check your status.', 'success');
          loadStats();
        } else if (r.body.errors) {
          Object.keys(r.body.errors).forEach(function (k) {
            var p = $('.field-error[data-for="' + k + '"]');
            if (p) p.textContent = r.body.errors[k];
          });
        } else { throw new Error(); }
      })
      .catch(function () { show(bookMsg, 'Something went wrong. Please try again in a moment.', 'error'); })
      .then(function () { bookBtn.disabled = false; });
  });

  // ---- Check status ----
  var checkForm = $('#check-form'), checkMsg = $('#check-msg'), checkBtn = $('#check-btn');
  checkForm.addEventListener('submit', function (e) {
    e.preventDefault();
    show(checkMsg, '');
    var ref = checkForm.elements['ref'].value.trim(), phone = checkForm.elements['cphone'].value.trim();
    if (!ref || !phone) { show(checkMsg, 'Enter your reference number and phone number.', 'error'); return; }
    checkBtn.disabled = true;

    fetch('/api/appointments/' + encodeURIComponent(ref) + '?phone=' + encodeURIComponent(phone))
      .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, status: res.status, body: body }; }); })
      .then(function (r) {
        if (r.ok) {
          var d = new Date(r.body.date + 'T00:00:00');
          show(checkMsg, r.body.department + ' on ' + d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) + '. Status: ' + r.body.status + '.', 'success');
        } else if (r.status === 404) {
          show(checkMsg, 'No matching appointment found. Check the reference and phone number.', 'error');
        } else { throw new Error(); }
      })
      .catch(function () { show(checkMsg, 'Something went wrong. Please try again in a moment.', 'error'); })
      .then(function () { checkBtn.disabled = false; });
  });

  checkStatus();
  setInterval(checkStatus, 15000);
  loadNotices();
  loadDepartments();
  loadStats();
})();
