(function () {
  var btn = document.querySelector('.menu-btn');
  var links = document.getElementById('links');
  if (btn && links) {
    btn.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
  }

  // Pipeline: stages complete one after another, once
  var stages = document.querySelectorAll('#pipeline .stage');
  var status = document.getElementById('pipe-status');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function finish() {
    if (status) { status.textContent = 'passed'; status.classList.add('ok'); }
  }
  if (reduce) {
    stages.forEach(function (s) { s.classList.add('done'); });
    finish();
  } else {
    stages.forEach(function (s, i) {
      setTimeout(function () {
        s.classList.add('active');
        setTimeout(function () {
          s.classList.remove('active'); s.classList.add('done');
          if (i === stages.length - 1) finish();
        }, 700);
      }, 500 + i * 900);
    });
  }

  var form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      var ok = form.name.value.trim() && form.email.value.includes('@') && form.message.value.trim().length >= 10;
      if (!ok) { e.preventDefault(); alert('Please enter your name, a valid email and a message of at least 10 characters.'); }
    });
  }
})();
