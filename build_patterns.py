#!/usr/bin/env python3
"""
Generate the six Override pattern pages from patterns.json.

Run:  python3 build_patterns.py

It does three things, all idempotent:
  1. Writes /pattern/<slug>/index.html for every pattern.
  2. Rewrites the PATTERNS object inside assessment.html, between its
     BEGIN/END marker comments, so the quiz and the pages always agree.
  3. Refreshes the pattern URLs in sitemap.xml, between its marker comments,
     leaving every other entry untouched.

patterns.json is the single source of truth. Edit copy there, never in the
generated files, then re-run this. Anything you hand-edit in /pattern/ or
inside the marker regions gets overwritten on the next run.
"""

import html
import json
import pathlib
import re
import datetime

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "patterns.json"
ASSESSMENT = ROOT / "assessment.html"
SITEMAP = ROOT / "sitemap.xml"
OUT_DIR = ROOT / "pattern"

SITE = "https://theoverride.co"
CALENDLY = "https://calendly.com/roblesinc/override-coaching-call"
GUIDE_PDF = "https://roblesmedia.github.io/the-override/override-starter-guide.pdf"
CF_BEACON = '5aa027499d2f482abd487a388cd352c8'

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
    '<link href="https://fonts.googleapis.com/css2?family=Archivo:ital,wght@0,400;0,600;0,800;0,900;1,800'
    '&family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet" />'
)

# Lifted from assessment.html so a pattern page is visually identical to the
# result screen it replaces.
CSS = """  :root{
    --black:#0a0a0a; --pure:#000; --white:#ffffff;
    --accent:#f0a500; --accent-dark:#c78700;
    --green:#1f3d33; --green-soft:#2c5446; --green-text:#7bbfa6;
    --muted:#7a7a7a; --muted2:#9a9a9a; --line:#1e1e1e; --card:#121212;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  html{-webkit-text-size-adjust:100%;}
  body{
    background:radial-gradient(1200px 600px at 80% -10%, #14241e 0%, transparent 60%), var(--black);
    color:var(--white);font-family:"Space Grotesk",sans-serif;line-height:1.5;
    min-height:100vh;display:flex;flex-direction:column;
  }
  a{color:inherit;}
  .wrap{width:100%;max-width:720px;margin:0 auto;padding:0 22px;}

  header{padding:22px 0;flex:0 0 auto;}
  .topbar{display:flex;align-items:center;justify-content:space-between;}
  .brand{font-family:"Archivo Black",sans-serif;text-transform:uppercase;font-size:18px;letter-spacing:-0.01em;text-decoration:none;}
  .brand span{color:var(--accent);}
  .back{font-size:12.5px;color:var(--muted2);text-decoration:none;text-transform:uppercase;letter-spacing:.1em;}
  .back:hover{color:var(--white);}

  main{flex:1 1 auto;padding:24px 0 60px;}
  .fade{animation:fade .4s ease both;}
  @keyframes fade{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}

  .btn{display:inline-block;font-family:"Archivo Black",sans-serif;text-transform:uppercase;letter-spacing:.02em;
    cursor:pointer;border:none;transition:transform .12s ease, background .15s ease;text-decoration:none;}
  .btn-accent{background:var(--accent);color:#000 !important;padding:17px 34px;border-radius:999px;font-size:16px;}
  .btn-accent:hover{transform:translateY(-2px) scale(1.02);}
  .btn-ghost{background:transparent;color:var(--white) !important;border:2px solid var(--line);padding:15px 30px;border-radius:999px;font-size:14px;}
  .btn-ghost:hover{border-color:var(--white);}

  .res-eyebrow{font-family:"Archivo",sans-serif;font-weight:800;text-transform:uppercase;letter-spacing:.2em;font-size:12px;color:var(--muted2);margin-bottom:12px;}
  .res-name{font-family:"Archivo Black",sans-serif;text-transform:uppercase;font-size:clamp(34px,6.5vw,58px);line-height:.98;}
  .res-name .gold{color:var(--accent);}
  .belief{font-family:"Archivo",sans-serif;font-style:italic;font-weight:800;color:var(--accent);
    font-size:clamp(20px,3vw,27px);margin-top:22px;line-height:1.25;padding-left:18px;
    border-left:3px solid var(--accent);max-width:600px;}
  .reframe{color:#e8e8e8;font-size:17px;line-height:1.6;margin-top:22px;max-width:580px;}

  .card{
    background:linear-gradient(180deg, rgba(31,61,51,0.35), rgba(18,18,18,0.6));
    border:1px solid var(--green-soft);border-radius:18px;padding:24px;margin-top:30px;
    box-shadow:0 24px 60px rgba(0,0,0,0.5);backdrop-filter:blur(6px);
  }
  .card h3{font-family:"Archivo",sans-serif;font-weight:800;font-size:18px;margin-bottom:6px;}
  .card p.sub{color:var(--muted2);font-size:14.5px;margin-bottom:16px;line-height:1.5;}

  .block{margin-top:26px;}
  .block .label{font-family:"Archivo",sans-serif;font-weight:800;text-transform:uppercase;letter-spacing:.16em;font-size:12px;margin-bottom:12px;}
  .block .label.gold{color:var(--accent);}
  .block .label.green{color:var(--green-text);}
  .block .label.gray{color:var(--muted2);}
  .rlist{list-style:none;display:flex;flex-direction:column;gap:9px;}
  .rlist li{position:relative;padding-left:22px;color:#dcdcdc;font-size:16px;line-height:1.5;}
  .rlist li:before{content:"";position:absolute;left:2px;top:9px;width:7px;height:7px;border-radius:50%;background:var(--muted);}
  .rlist.gold li:before{background:var(--accent);}
  .rlist.green li:before{background:var(--green-text);}
  /* The three lists get three different weights so the middle of the page stops
     reading as one undifferentiated block. */
  .block.cost .rlist{background:rgba(240,165,0,0.045);border-left:2px solid rgba(240,165,0,0.4);
    border-radius:0 12px 12px 0;padding:17px 20px;}
  .rlist.arrows li{padding-left:24px;color:#e8e8e8;}
  .rlist.arrows li:before{content:"\\2192";background:none;width:auto;height:auto;border-radius:0;
    top:0;left:0;color:var(--green-text);font-weight:700;font-size:15px;}

  /* ---- the Override Method, drawn ---- */
  .method{margin-top:44px;padding-top:30px;border-top:1px solid var(--line);}
  .method .label{font-family:"Archivo",sans-serif;font-weight:800;text-transform:uppercase;
    letter-spacing:.16em;font-size:12px;margin-bottom:12px;}
  .method .label.gold{color:var(--accent);}
  .method .label.green{color:var(--green-text);}
  .method-intro{color:var(--muted2);font-size:14.5px;line-height:1.55;margin-bottom:26px;max-width:560px;}
  .flow{position:relative;padding-left:26px;}
  .flow:before{content:"";position:absolute;left:5px;top:9px;bottom:9px;width:2px;background:var(--line);}
  .flow-old{padding-left:52px;margin-bottom:10px;}
  .flow-old:before{left:31px;background:rgba(240,165,0,0.35);}
  .flow-new:before{background:rgba(123,191,166,0.35);}
  .step{position:relative;padding-bottom:19px;}
  .step:last-child{padding-bottom:0;}
  .step:before{content:"";position:absolute;top:6px;width:12px;height:12px;border-radius:50%;
    background:var(--black);border:2px solid var(--muted);}
  .flow-old .step:before{left:-52px;margin-left:26px;border-color:var(--accent);}
  .flow-new .step:before{left:-26px;border-color:var(--green-text);}
  .flow-new .step:last-child:before{background:var(--green-text);}
  .step .k{font-family:"Archivo",sans-serif;font-weight:800;text-transform:uppercase;
    letter-spacing:.14em;font-size:11px;display:block;margin-bottom:3px;}
  .flow-old .step .k{color:var(--accent);}
  .flow-new .step .k{color:var(--green-text);}
  .step p{color:#dcdcdc;font-size:15.5px;line-height:1.45;}
  /* The return path: the old loop closes back on itself. */
  .flow-old .arc{position:absolute;left:0;top:12px;bottom:22px;width:24px;
    border:2px solid var(--accent);border-right:0;border-radius:13px 0 0 13px;opacity:.5;}
  .flow-old .arc:after{content:"";position:absolute;left:22px;top:-6px;width:0;height:0;
    border:5px solid transparent;border-left-color:var(--accent);}
  .loop-back{margin-top:13px;margin-left:52px;font-family:"Archivo",sans-serif;font-weight:800;
    font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--accent);opacity:.75;}
  .break-out{margin-top:13px;margin-left:26px;font-family:"Archivo",sans-serif;font-weight:800;
    font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--green-text);}
  .method-gap{height:26px;}
  .secondary{margin-top:26px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted2);font-size:14.5px;line-height:1.5;display:none;}
  .secondary b{color:var(--white);font-weight:600;}
  .res-cta{margin-top:30px;display:flex;gap:14px;flex-wrap:wrap;align-items:center;}

  .others{margin-top:44px;padding-top:26px;border-top:1px solid var(--line);}
  .others .label{font-family:"Archivo",sans-serif;font-weight:800;text-transform:uppercase;letter-spacing:.16em;font-size:12px;color:var(--muted2);margin-bottom:14px;}
  .others .row{display:flex;flex-wrap:wrap;gap:8px;}
  .others a{border:1px solid var(--line);border-radius:999px;padding:7px 14px;font-size:13px;color:#cfcfcf;
    background:rgba(255,255,255,0.02);text-decoration:none;transition:border-color .14s,color .14s;}
  .others a:hover{border-color:var(--accent);color:var(--white);}
  .coldcta{margin-top:18px;color:var(--muted);font-size:13.5px;}
  .coldcta a{color:var(--muted2);text-decoration:underline;}
  .coldcta a:hover{color:var(--white);}

  footer{flex:0 0 auto;padding:26px 0;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;text-align:center;}
  footer a{color:var(--muted2);}
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<title>{seo_title} | The Override</title>
<meta name="description" content="{seo_desc}" />
<link rel="canonical" href="{site}/pattern/{slug}/" />
<link rel="icon" href="/favicon.png" />
<meta property="og:type" content="article" />
<meta property="og:title" content="{seo_title} | The Override" />
<meta property="og:description" content="{seo_desc}" />
<meta property="og:url" content="{site}/pattern/{slug}/" />
<meta property="og:image" content="{site}/og.png" />
<meta name="twitter:card" content="summary_large_image" />
{fonts}
<style>
{css}</style>
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "{beacon}"}}'></script><!-- End Cloudflare Web Analytics -->
</head>
<body>
<header>
  <div class="wrap topbar">
    <a class="brand" href="/">THE<span>OVERRIDE</span></a>
    <a class="back" href="/">&larr; Home</a>
  </div>
</header>

<main>
  <div class="wrap fade">
    <div class="res-eyebrow" id="eyebrow">Your primary pattern</div>
    <div class="res-name">{gold_name}</div>
    <div class="belief">{belief}</div>
    <p class="reframe">{reframe}</p>

    <div class="block"><div class="label gray">What this pattern gives you</div>
{gives}    </div>
    <div class="block cost"><div class="label gold">What it costs you</div>
{costs}    </div>
    <div class="block"><div class="label green">The override</div>
{override}    </div>

    <section class="method">
      <div class="label gold">The loop you're running</div>
      <p class="method-intro">Every pattern runs the same way. Something sets it off, a story fires,
        the behavior follows, and it feeds the next round. Here is yours, and here is where it breaks.</p>
      <div class="flow flow-old">
        <span class="arc" aria-hidden="true"></span>
        <div class="step"><span class="k">Trigger</span><p>{l_trigger}</p></div>
        <div class="step"><span class="k">Story</span><p>{l_story}</p></div>
        <div class="step"><span class="k">Pattern</span><p>{l_pattern}</p></div>
      </div>
      <div class="loop-back">and around again</div>

      <div class="method-gap"></div>

      <div class="label green">Where you break it</div>
      <div class="flow flow-new">
        <div class="step"><span class="k">Pause</span><p>{l_pause}</p></div>
        <div class="step"><span class="k">Override</span><p>{l_override}</p></div>
        <div class="step"><span class="k">New action</span><p>{l_action}</p></div>
      </div>
      <div class="break-out">out of the loop</div>
    </section>

    <div class="secondary" id="secondary"></div>

    <div class="card" style="border-color:var(--accent);">
      <h3>Ready to actually override it?</h3>
      <p class="sub">The fastest way forward is a real conversation. Book a free call with David. You'll leave it clearer than you came.</p>
      <a class="btn btn-accent" href="{calendly}" target="_blank" rel="noopener" style="width:100%;text-align:center;">Book your free consultation</a>
    </div>

    <div class="res-cta">
      <a class="btn btn-ghost" href="{guide}" target="_blank" rel="noopener">Get the free guide</a>
    </div>

    <div class="others">
      <div class="label">The other patterns</div>
      <div class="row">
{others}      </div>
      <!-- Shown only to someone who did not arrive from the quiz. Without it a
           visitor from search has no way into the assessment at all. -->
      <p class="coldcta" id="coldCta">Not sure this one is yours? <a href="/assessment.html">Take the 2-minute assessment</a>.</p>
    </div>
  </div>
</main>

<footer>
  <div class="wrap">The Override is coaching, not therapy. &nbsp;&middot;&nbsp; <a href="/">theoverride.co</a></div>
</footer>

<script>
// Personalize for someone arriving straight from the assessment. Their name and
// secondary pattern are handed over in sessionStorage, never in the URL, so a
// link they share carries no personal information. Anyone landing cold from
// search just sees the generic page.
(function(){{
  var NAMES={names_js};
  try{{
    var n=sessionStorage.getItem('ovName');
    var sec=sessionStorage.getItem('ovSecondary');
    if(n){{
      document.getElementById('eyebrow').textContent=n+", here's your pattern";
      var c=document.getElementById('coldCta'); if(c) c.style.display='none';
    }}
    if(sec&&NAMES[sec]){{
      var el=document.getElementById('secondary');
      el.innerHTML='You also carry a strong streak of <b>'+NAMES[sec].name+'</b>. '+NAMES[sec].belief+
        ' Most people are a blend; this is the one running second. '+
        '<a href="/pattern/'+sec+'/" style="color:var(--accent);">See it &rarr;</a>';
      el.style.display='block';
    }}
  }}catch(_){{}}
}})();
</script>
</body>
</html>
"""


def gold(name: str) -> str:
    """'The Achiever' -> 'The <span class="gold">Achiever</span>' to match the quiz."""
    if name.startswith("The "):
        return 'The <span class="gold">' + html.escape(name[4:], quote=False) + "</span>"
    return html.escape(name, quote=False)


def ul(items, cls=""):
    lis = "".join(
        '        <li>{}</li>\n'.format(html.escape(i, quote=False)) for i in items
    )
    return '      <ul class="rlist {}">\n{}      </ul>\n'.format(cls, lis)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    patterns = data["patterns"]
    order = data["order"]
    today = datetime.date.today().isoformat()

    # Name/belief lookup the pages use to describe a secondary pattern.
    names_js = json.dumps(
        {k: {"name": v["name"], "belief": v["belief"]} for k, v in patterns.items()},
        ensure_ascii=True,
    )

    # ---- 1. the six pages -------------------------------------------------
    OUT_DIR.mkdir(exist_ok=True)
    written = []
    for slug in order:
        p = patterns[slug]
        others = "".join(
            '        <a href="/pattern/{}/">{}</a>\n'.format(
                o, html.escape(patterns[o]["name"], quote=False)
            )
            for o in order
            if o != slug
        )
        page = PAGE.format(
            site=SITE,
            slug=slug,
            seo_title=html.escape(p["seoTitle"], quote=True),
            seo_desc=html.escape(p["seoDescription"], quote=True),
            fonts=FONTS,
            css=CSS,
            beacon=CF_BEACON,
            gold_name=gold(p["name"]),
            belief=html.escape(p["belief"], quote=False),
            reframe=html.escape(p["reframe"], quote=False),
            gives=ul(p["gives"]),
            costs=ul(p["costs"], "gold"),
            override=ul(p["override"], "green arrows"),
            l_trigger=html.escape(p["loop"]["trigger"], quote=False),
            l_story=html.escape(p["loop"]["story"], quote=False),
            l_pattern=html.escape(p["loop"]["pattern"], quote=False),
            l_pause=html.escape(p["loop"]["pause"], quote=False),
            l_override=html.escape(p["loop"]["override"], quote=False),
            l_action=html.escape(p["loop"]["action"], quote=False),
            calendly=CALENDLY,
            guide=GUIDE_PDF,
            others=others,
            names_js=names_js,
        )
        d = OUT_DIR / slug
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page, encoding="utf-8")
        written.append("pattern/{}/index.html".format(slug))

    # ---- 2. sync the quiz's PATTERNS object -------------------------------
    # json.dumps with ensure_ascii=True emits pure 7-bit JS, so the curly quotes
    # in the copy land as \u escapes and cannot corrupt the file.
    quiz_obj = {
        k: {
            "name": v["name"],
            "belief": v["belief"],
            "reframe": v["reframe"],
            "gives": v["gives"],
            "costs": v["costs"],
            "override": v["override"],
        }
        for k, v in patterns.items()
    }
    block = "  var PATTERNS=" + json.dumps(quiz_obj, ensure_ascii=True) + ";\n"
    src = ASSESSMENT.read_text(encoding="utf-8")
    new, n = re.subn(
        r"(// BEGIN:patterns\n).*?(  // END:patterns)",
        lambda m: m.group(1) + block + m.group(2),
        src,
        flags=re.DOTALL,
    )
    if n != 1:
        raise SystemExit(
            "assessment.html: expected exactly 1 BEGIN:patterns/END:patterns region, found {}".format(n)
        )
    if new != src:
        ASSESSMENT.write_text(new, encoding="utf-8")

    # ---- 3. sitemap -------------------------------------------------------
    entries = "".join(
        "  <url>\n"
        "    <loc>{}/pattern/{}/</loc>\n"
        "    <lastmod>{}</lastmod>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>0.7</priority>\n"
        "  </url>\n".format(SITE, slug, today)
        for slug in order
    )
    sm = SITEMAP.read_text(encoding="utf-8")
    region = "  <!-- BEGIN:patterns -->\n" + entries + "  <!-- END:patterns -->\n"
    if "<!-- BEGIN:patterns -->" in sm:
        sm = re.sub(
            r"  <!-- BEGIN:patterns -->\n.*?  <!-- END:patterns -->\n",
            lambda _: region,
            sm,
            flags=re.DOTALL,
        )
    else:
        sm = sm.replace("</urlset>", region + "</urlset>")
    SITEMAP.write_text(sm, encoding="utf-8")

    print("Wrote {} pages:".format(len(written)))
    for w in written:
        print("  " + w)
    print("Synced assessment.html PATTERNS block and sitemap.xml.")


if __name__ == "__main__":
    main()
