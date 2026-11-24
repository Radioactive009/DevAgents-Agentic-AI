from flask import Flask, render_template, render_template_string

CSS = """:root{--bg:#0f172a;--card:#1e293b;--accent:#22d3ee;--text:#e2e8f0}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.wrap{width:100%}
nav{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;padding:1rem 1.5rem;background:var(--card);position:sticky;top:0}
.brand{font-weight:700;font-size:1.25rem;color:var(--accent)}
.menu-btn{display:inline-block;background:none;border:1px solid var(--accent);color:var(--accent);padding:.4rem .8rem;border-radius:6px;cursor:pointer}
.menu{display:none;width:100%;padding-top:.5rem}
.menu.open{display:block}
.menu a{display:block;padding:.5rem;color:var(--text);text-decoration:none}
.hero,.classes,.pricing,.contact{padding:3rem 1.5rem}
.hero h1{font-size:2.2rem}
.card-row{display:grid;gap:1rem;grid-template-columns:1fr;margin-top:1rem}
.card{background:var(--card);padding:1.5rem;border-radius:10px}
.card h3{color:var(--accent)}
.btn{display:inline-block;margin-top:1rem;background:var(--accent);color:#04262b;padding:.6rem 1.2rem;border:none;border-radius:6px;cursor:pointer;font-weight:700}
footer{padding:1.5rem;text-align:center;background:var(--card)}
@media(min-width:768px){.menu-btn{display:none}.menu{display:flex;width:auto;padding-top:0}.menu a{padding:0 1rem}.card-row{grid-template-columns:repeat(3,1fr)}.hero h1{font-size:3rem}}
"""

JS = """(function(){var b=document.querySelector('.menu-btn');var m=document.querySelector('.menu');if(b&&m){b.addEventListener('click',function(){m.classList.toggle('open');});}})();"""

INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Movements Gym</title>
<style>%(css)s</style>
</head>
<body class="wrap">
<header>
<nav aria-label="main">
<span class="brand">Movements Gym</span>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu">Menu</button>
<div class="menu" id="menu">
<a class="nav-link" href="#classes">Classes</a>
<a class="nav-link" href="#pricing">Pricing</a>
<a class="nav-link" href="#contact">Contact</a>
</div>
</nav>
</header>
<main>
<section class="hero">
<h1>Train Smarter. Move Better.</h1>
<p>Strength, conditioning, and mobility in one modern gym.</p>
<button class="btn" type="button">Join Now</button>
</section>
<section class="classes" id="classes">
<h2>Classes</h2>
<div class="card-row">
<div class="card"><h3>Strength</h3><p>Build power with coached lifting.</p></div>
<div class="card"><h3>Conditioning</h3><p>Improve engine and endurance.</p></div>
<div class="card"><h3>Mobility</h3><p>Move well and stay healthy.</p></div>
</div>
</section>
<section class="pricing" id="pricing">
<h2>Pricing</h2>
<div class="card-row">
<div class="card"><h3>Monthly</h3><p>$59 / month</p><button class="btn" type="button">Select</button></div>
<div class="card"><h3>Quarterly</h3><p>$150 / quarter</p><button class="btn" type="button">Select</button></div>
<div class="card"><h3>Annual</h3><p>$550 / year</p><button class="btn" type="button">Select</button></div>
</div>
</section>
<section class="contact" id="contact">
<h2>Contact</h2>
<p>Email us at hello@movements.example or call (555) 000-0000.</p>
</section>
</main>
<footer>
<p>&copy; 2025 Movements Gym</p>
</footer>
<script>%(js)s</script>
</body>
</html>
"""


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template_string(INDEX, css=CSS, js=JS)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
