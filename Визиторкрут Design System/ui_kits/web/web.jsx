/* Визиторкрут — Web (marketing) UI kit. Reads window.DesignSystem_ee81bc.
   Landing page for vizitorkrut.ru. Layout classes (.w-*) live in index.html. */
(function () {
  const DS = window.DesignSystem_ee81bc;
  const { Button, Icon, Card, Verdict, Metric, Badge, Tag } = DS;

  const AUDIENCES = [
    { icon: 'stethoscope', label: 'Врачам', text: 'Вызов на дом окупит дорогу — или лучше остаться на приёме.' },
    { icon: 'car-front', label: 'Таксистам', text: 'Видно, где тариф съест бензин и пробки, ещё до подачи.' },
    { icon: 'package', label: 'Курьерам', text: 'Пачка заказов по пути или один невыгодный крюк — сразу понятно.' },
    { icon: 'wrench', label: 'Мастерам', text: 'Далёкий вызов за копейки отсекается до того, как ты выехал.' },
  ];

  const STEPS = [
    { icon: 'inbox', n: '01', h: 'Приходит заказ', t: 'Адрес, оплата, расстояние — как везде.' },
    { icon: 'gauge', n: '02', h: 'Считаем вердикт', t: 'Минус бензин, износ и время в пути — по твоим настройкам.' },
    { icon: 'navigation', n: '03', h: 'Ты решаешь', t: 'Стоит — берёшь. Не стоит — ждёшь следующий. Без догадок.' },
  ];

  function Phone() {
    const Row = ({ prof, icon, level, title, pay, per }) => (
      <Card padding="sm" style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
            <Icon name={icon} size={14} /> {prof}
          </span>
          <Verdict level={level} size="sm" />
        </div>
        <div style={{ fontSize: 14, fontWeight: 700 }}>{title}</div>
        <div style={{ display: 'flex', gap: 16, borderTop: '1px solid var(--border-subtle)', paddingTop: 6 }}>
          <Metric label="Оплата" value={pay} unit="₽" tone="brand" size="sm" />
          <Metric label="Чистыми/ч" value={'₽' + per} tone={level === 'skip' ? 'skip' : 'go'} size="sm" />
        </div>
      </Card>
    );
    return (
      <div className="w-phone">
        <div className="w-phone-top">
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Лента · 3 стоящих</span>
          <Badge variant="success" dot size="sm">На смене</Badge>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Row prof="Врач" icon="stethoscope" level="go" title="Вызов на дом · Пресня" pay="3 200" per="980" />
          <Row prof="Такси" icon="car-front" level="go" title="До Шереметьево" pay="2 480" per="640" />
          <Row prof="Мастер" icon="wrench" level="skip" title="Сборка · Бутово" pay="1 500" per="280" />
        </div>
      </div>
    );
  }

  function App() {
    return (
      <div className="w-page">
        {/* nav */}
        <header className="w-nav">
          <div className="w-container w-nav-inner">
            <span className="w-wordmark">Визиторкрут</span>
            <nav className="w-nav-links">
              <a href="#audience">Для кого</a>
              <a href="#how">Как работает</a>
              <a href="#calc">Расчёт</a>
            </nav>
            <div className="w-nav-cta">
              <Button variant="ghost" size="sm">Войти</Button>
              <Button variant="primary" size="sm" iconLeft={<Icon name="download" size={16} />}>Скачать</Button>
            </div>
          </div>
        </header>

        {/* hero */}
        <section className="w-hero">
          <div className="w-container w-hero-grid">
            <div className="w-hero-copy">
              <span className="w-eyebrow">Приложение для выездных работников</span>
              <h1 className="w-h1">Стоит ли вообще<br/><span className="w-accent">туда ехать?</span></h1>
              <p className="w-lead">Навигатор показывает, куда ехать. Визиторкрут показывает — <b>стоит ли</b>. Считаем твой честный заработок за час с учётом бензина, износа и пробок — до того, как ты возьмёшь заказ.</p>
              <div className="w-cta-row">
                <Button variant="primary" size="lg" iconLeft={<Icon name="smartphone" size={20} />}>Скачать бесплатно</Button>
                <Button variant="secondary" size="lg" iconRight={<Icon name="play" size={18} />}>Как это работает</Button>
              </div>
              <div className="w-hero-note">
                <Icon name="shield-check" size={16} /> Бесплатно · без привязки к агрегатору
              </div>
            </div>
            <div className="w-hero-visual"><Phone /></div>
          </div>
        </section>

        {/* audience */}
        <section className="w-section" id="audience">
          <div className="w-container">
            <span className="w-eyebrow w-center">Для кого</span>
            <h2 className="w-h2 w-center">Один выезд — одно решение.<br/>Для всех, кто зарабатывает в дороге.</h2>
            <div className="w-aud-grid">
              {AUDIENCES.map((a) => (
                <Card key={a.label} padding="lg" className="w-aud-card">
                  <span className="w-aud-ico"><Icon name={a.icon} size={26} strokeWidth={1.9} /></span>
                  <h3 className="w-aud-h">{a.label}</h3>
                  <p className="w-aud-t">{a.text}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* how */}
        <section className="w-section w-section-sunken" id="how">
          <div className="w-container">
            <span className="w-eyebrow w-center">Как работает</span>
            <h2 className="w-h2 w-center">Три секунды на решение</h2>
            <div className="w-steps">
              {STEPS.map((s) => (
                <div key={s.n} className="w-step">
                  <span className="w-step-ico"><Icon name={s.icon} size={26} strokeWidth={1.9} /></span>
                  <span className="w-step-n">{s.n}</span>
                  <h3 className="w-step-h">{s.h}</h3>
                  <p className="w-step-t">{s.t}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* calc / feature */}
        <section className="w-section" id="calc">
          <div className="w-container w-feature">
            <div className="w-feature-copy">
              <span className="w-eyebrow">Честный ₽ в час</span>
              <h2 className="w-h2">Мы вычитаем то,<br/>что прячут агрегаторы</h2>
              <p className="w-lead">Оплата за заказ — это не то, что ты заработаешь. Мы отнимаем бензин по твоей цене, износ машины и время в пути с пробками. Остаётся честная цифра — сколько реально упадёт в карман за час.</p>
              <ul className="w-list">
                <li><Icon name="check" size={18} /> Твоя цена бензина и расход</li>
                <li><Icon name="check" size={18} /> Пробки в реальном времени</li>
                <li><Icon name="check" size={18} /> Порог «стоит / не стоит» под тебя</li>
              </ul>
            </div>
            <Card variant="raised" padding="lg" className="w-breakdown">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <div>
                  <div style={{ fontSize: 17, fontWeight: 700 }}>До Шереметьево</div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Тверская, 12 → SVO · 38 км</div>
                </div>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}><Icon name="car-front" size={16} /> Такси</span>
              </div>
              {[['Тариф', '+2 480'], ['Бензин 38 км', '−420'], ['Время в пути 44 мин', '−410']].map(([k, v], i) => (
                <div key={i} className="w-brk-row">
                  <span>{k}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: v[0] === '+' ? 'var(--verdict-go-text)' : 'var(--verdict-skip-text)' }}>{v} ₽</span>
                </div>
              ))}
              <div className="w-brk-total">
                <span>Чистыми в час</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 26, color: 'var(--brand)' }}>₽640</span>
              </div>
              <Verdict level="go" reason="Выше твоей нормы ₽500/ч — бери." />
            </Card>
          </div>
        </section>

        {/* stats band */}
        <section className="w-stats-band">
          <div className="w-container w-stats">
            {[['1,2 млн', 'выездов оценено'], ['+34%', 'к среднему ₽/ч у водителей'], ['48', 'городов России']].map(([v, l], i) => (
              <div key={i} className="w-stat">
                <div className="w-stat-v">{v}</div>
                <div className="w-stat-l">{l}</div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="w-ctaband">
          <div className="w-container w-cta-inner">
            <h2 className="w-cta-h">Хватит ездить впустую</h2>
            <p className="w-cta-sub">Поставь приложение и посмотри первый вердикт за минуту.</p>
            <div className="w-cta-row">
              <Button variant="primary" size="xl" iconLeft={<Icon name="download" size={20} />}>Скачать Визиторкрут</Button>
            </div>
          </div>
        </section>

        {/* footer */}
        <footer className="w-footer">
          <div className="w-container w-foot-grid">
            <div>
              <span className="w-wordmark w-wordmark-inv">Визиторкрут</span>
              <p className="w-foot-tag">Навигатор показывает, куда ехать.<br/>Мы — стоит ли.</p>
            </div>
            <div className="w-foot-col">
              <h4>Продукт</h4>
              <a href="#how">Как работает</a>
              <a href="#calc">Расчёт ₽/ч</a>
              <a href="#audience">Для кого</a>
            </div>
            <div className="w-foot-col">
              <h4>Компания</h4>
              <a href="#">О нас</a>
              <a href="#">Блог</a>
              <a href="#">Вакансии</a>
            </div>
            <div className="w-foot-col">
              <h4>Помощь</h4>
              <a href="#">Поддержка</a>
              <a href="#">Договор</a>
              <a href="#">vizitorkrut.ru</a>
            </div>
          </div>
          <div className="w-container w-foot-legal">
            <span>© 2026 Визиторкрут</span>
            <span>Сделано для тех, кто в дороге</span>
          </div>
        </footer>
      </div>
    );
  }

  window.VKWeb = App;
})();
