"""Run against localhost:8000, fresh TP DB recommended. Optional BASE_URL."""
import os, time
from playwright.sync_api import sync_playwright,expect
BASE=os.getenv('BASE_URL','http://localhost:8000')
with sync_playwright() as p:
    browser=p.chromium.launch(args=['--no-sandbox'])
    errors=[];suffix=str(time.time_ns())[-8:]
    contexts=[browser.new_context() for _ in range(3)]
    pages=[c.new_page() for c in contexts]
    # Emulate missing recent APIs without relaxing CSP or disabling crypto.
    for page in pages:
        page.add_init_script("Object.hasOwn=undefined;AbortSignal.timeout=undefined;crypto.randomUUID=undefined;if(window.HTMLDialogElement){HTMLDialogElement.prototype.showModal=undefined;HTMLDialogElement.prototype.close=undefined;}")
        page.on('pageerror',lambda e:errors.append(str(e)))
    def register(page,name):
        page.goto(BASE);page.locator('#auth-toggle').click()
        page.locator('#nick').fill(name);page.locator('#pass').fill('abcd1');page.locator('#join-button').click()
        expect(page.locator('#room-panel')).to_be_visible()
    def enter(page,code):
        page.locator('#room-code').fill(code);page.locator('#room-join').click();expect(page.locator('#connection')).to_contain_text('Connecté',timeout=15000)
    a,b,c=pages;names=['Alice'+suffix,'Bob'+suffix,'Other'+suffix]
    for page,name in zip(pages,names):register(page,name)
    # Invalid room visibly rejected.
    a.locator('#room-code').fill('abc');a.locator('#room-join').click();expect(a.locator('#room-error')).to_contain_text('Code invalide')
    enter(a,'1111a');enter(b,'1111A');enter(c,'0000E')
    expect(a.locator('#members li')).to_have_count(2);expect(c.locator('#members li')).to_have_count(1)
    a.locator('#text').fill('Bonjour <img src=x onerror=alert(1)>');a.locator('#send').click()
    expect(b.locator('.message p')).to_have_text('Bonjour <img src=x onerror=alert(1)>')
    assert c.locator('.message').count()==0;assert b.locator('#messages img').count()==0
    a.locator('#text').fill('/quit');a.locator('#send').click();expect(a.locator('#room-panel')).to_be_visible()
    assert a.locator('.message').count()==0
    expect(b.locator('.message')).to_have_count(1)
    enter(a,'1111A');assert a.locator('.message').count()==0
    a.locator('#leave').click();a.locator('#logout').click();expect(a.locator('#auth-card')).to_be_visible()
    a.locator('#nick').fill(names[0]);a.locator('#pass').fill('wrong1');a.locator('#join-button').click();expect(a.locator('#join-error')).to_contain_text('incorrect')
    a.locator('#pass').fill('abcd1');a.locator('#join-button').click();expect(a.locator('#room-panel')).to_be_visible()
    a.reload();expect(a.locator('#room-panel')).to_be_visible()
    a.locator('#lang').click();expect(a.locator('label[for=room-code]')).to_have_text('Room code')
    a.locator('#theme').click();expect(a.locator('html')).to_have_attribute('data-theme','dark')
    a.set_viewport_size({'width':375,'height':667});a.emulate_media(reduced_motion='reduce')
    assert a.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # Service and network failures must not be labelled as generic startup errors.
    a.route('**/api/config',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"serverError"}'))
    a.locator('#room-code').fill('1111A');a.locator('#room-join').click();expect(a.locator('#room-error')).to_contain_text('Server error')
    a.unroute('**/api/config');a.route('**/api/config',lambda route:route.abort())
    a.locator('#room-join').click();expect(a.locator('#room-error')).to_contain_text('Network unavailable')
    a.locator('#about-open').click();expect(a.locator('#about')).to_be_visible();a.locator('#about-close').click();expect(a.locator('#about')).not_to_be_visible()
    blocked=browser.new_page();blocked.goto(BASE)
    blocked.route('**/api/me',lambda route:route.fulfill(status=401,content_type='application/json',body='{"detail":"authRequired"}'))
    blocked.locator('#auth-toggle').click();blocked.locator('#nick').fill('Blocked'+suffix);blocked.locator('#pass').fill('abcd1');blocked.locator('#join-button').click()
    expect(blocked.locator('#join-error')).to_contain_text('cookies')
    assert not errors,errors
    browser.close()
print('PASS: accounts, wrong password, session reload, room isolation, encryption, safe text, quit/local wipe, no history, FR/EN, dark/mobile/reduced-motion, missing recent APIs, network/503 errors')
