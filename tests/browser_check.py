"""Run explicitly against a running local server: python tests/browser_check.py."""
from playwright.sync_api import sync_playwright, expect
from pathlib import Path

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    errors=[]
    packets=[]
    a=browser.new_page();b=browser.new_page();c=browser.new_page()
    for page in (a,b,c):
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_init_script("const W=window.WebSocket;window.WebSocket=class extends W {constructor(...a){super(...a);window.testSocket=this;}}")
    def login(page,nick,secret='une phrase longue et forte1'):
        page.goto('http://localhost:8000');page.locator('#nick').fill(nick);page.locator('#pass').fill(secret);page.locator('#join-button').click();expect(page.locator('#connection')).to_contain_text('Connecté')
    a.on('websocket',lambda ws: ws.on('framesent',lambda data:packets.append(data)))
    a.goto('http://localhost:8000');expect(a.locator('html')).to_have_attribute('lang','fr')
    a.locator('#theme').click();expect(a.locator('html')).to_have_attribute('data-theme','dark')
    a.locator('#lang').click();expect(a.locator('h1')).to_have_text('Conversation, kept discreet.')
    a.locator('#lang').click();a.locator('#theme').click();expect(a.locator('html')).to_have_attribute('data-theme','light');a.locator('#theme').click();expect(a.locator('#landing')).to_have_css('opacity','1');a.screenshot(path='docs/home-dark.png',full_page=True)
    login(a,'Alice');login(b,'Bob');expect(a.locator('#members li')).to_have_count(2)
    a.locator('#text').fill('Bonjour <img src=x onerror=alert(1)>');a.locator('#send').click()
    expect(b.locator('.message p')).to_have_text('Bonjour <img src=x onerror=alert(1)>')
    assert b.locator('#messages img').count()==0
    assert not any('Bonjour' in x for x in packets)
    login(c,'Charlie','une autre phrase très longue2')
    a.locator('#text').fill('Second message');a.locator('#send').click()
    expect(c.locator('.event[data-key=decrypt]')).to_be_visible()
    assert c.locator('.message').count()==0
    b.locator('#text').fill('/quit');b.locator('#send').click();expect(b.locator('#landing')).to_be_visible();expect(a.locator('#members li')).to_have_count(2)
    a.evaluate('window.testSocket.close()')
    expect(a.locator('#connection')).to_contain_text('interrompue')
    expect(a.locator('#connection')).to_contain_text('Connecté',timeout=10000)
    a.locator('#text').fill('Après reconnexion');a.locator('#send').click()
    expect(a.locator('.message p').last).to_have_text('Après reconnexion')
    a.screenshot(path='docs/chat.png',full_page=True)
    mobile=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce');mobile.goto('http://localhost:8000')
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert mobile.locator('#landing').evaluate("e=>getComputedStyle(e).animationName")=='none'
    mobile.screenshot(path='docs/home-mobile.png',full_page=True)
    login(mobile,'Mobile');mobile.locator('#members-toggle').click();expect(mobile.locator('#sidebar')).to_be_visible()
    mobile.locator('#members-toggle').click();expect(mobile.locator('#sidebar')).not_to_be_visible()
    a.evaluate("""const box=document.querySelector('#messages');for(let i=0;i<30;i++){let p=document.createElement('p');p.textContent='Local scroll test '+i;p.style.height='40px';box.append(p);}box.scrollTop=0;""")
    before=a.locator('#messages').evaluate('e=>e.scrollTop')
    mobile.locator('#text').fill('Défilement préservé');mobile.locator('#send').click()
    expect(a.locator('.message p').last).to_have_text('Défilement préservé')
    assert a.locator('#messages').evaluate('e=>e.scrollTop')==before
    expect(a.locator('#new-messages')).to_be_visible()
    short=browser.new_page();login(short,'Short','abcd1');short.locator('#leave').click()
    assert not errors,errors
    browser.close()
    print('PASS: FR/EN, dark theme, 3 clients, plaintext rendered safely, decryption failure, /quit, presence, mobile overflow, reduced-motion; no JS errors')
