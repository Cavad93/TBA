/* Визиторкрут — App UI kit. Single-file app: reads window.VK (data),
   window.DesignSystem_ee81bc (components), window.IOSDevice (frame). */
(function () {
  const DS = window.DesignSystem_ee81bc;
  const { Button, IconButton, Icon, Verdict, Metric, Card, Badge, Tag, Switch, Tabs, Input, Select, Checkbox, Toast } = DS;
  const { professions: PROF, jobs: JOBS, earnings: EARN } = window.VK;

  const fmt = (n) => Math.round(n).toLocaleString('ru-RU');
  const toneFor = (lvl) => (lvl === 'go' ? 'go' : lvl === 'skip' ? 'skip' : 'default');

  // ── shared bits ───────────────────────────────────────────
  function ScreenShell({ children }) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
        background: 'var(--paper)', fontFamily: 'var(--font-sans)', color: 'var(--text-primary)' }}>
        {children}
      </div>
    );
  }

  function TopBar({ title, sub, back, onBack, right }) {
    return (
      <div style={{ paddingTop: 56, padding: '56px 16px 12px', flex: 'none',
        borderBottom: '1px solid var(--border-subtle)', background: 'var(--paper)',
        display: 'flex', alignItems: 'center', gap: 12 }}>
        {back && (
          <IconButton aria-label="Назад" variant="ghost" onClick={onBack}><Icon name="arrow-left" /></IconButton>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          {sub && <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{sub}</div>}
          <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1.15 }}>{title}</div>
        </div>
        {right}
      </div>
    );
  }

  function Main({ children, pad = true }) {
    return (
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto',
        padding: pad ? '16px 16px 24px' : 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {children}
      </div>
    );
  }

  function TabBar({ tab, onTab, hasTrip }) {
    const items = [
      { k: 'feed', label: 'Лента', icon: 'layout-list' },
      { k: 'trip', label: 'В пути', icon: 'navigation' },
      { k: 'earn', label: 'Смена', icon: 'wallet' },
      { k: 'profile', label: 'Профиль', icon: 'user-round' },
    ];
    return (
      <div style={{ flex: 'none', display: 'flex', paddingBottom: 22,
        borderTop: '1px solid var(--border-default)', background: 'var(--color-surface)' }}>
        {items.map((it) => {
          const active = tab === it.k;
          return (
            <button key={it.k} onClick={() => onTab(it.k)} style={{
              flex: 1, border: 'none', background: 'none', cursor: 'pointer',
              padding: '10px 0 4px', display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 3, position: 'relative',
              color: active ? 'var(--brand)' : 'var(--text-tertiary)' }}>
              <div style={{ position: 'relative' }}>
                <Icon name={it.icon} size={23} strokeWidth={active ? 2.25 : 1.9} />
                {it.k === 'trip' && hasTrip && (
                  <span style={{ position: 'absolute', top: -2, right: -4, width: 8, height: 8,
                    borderRadius: '50%', background: 'var(--brand)', border: '1.5px solid var(--color-surface)' }} />
                )}
              </div>
              <span style={{ fontSize: 11, fontWeight: 600 }}>{it.label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  function MapView({ height = 200, radius = 16 }) {
    return (
      <div style={{ position: 'relative', height, borderRadius: radius, overflow: 'hidden',
        border: '1px solid var(--border-default)', background: '#E7E3D8',
        backgroundImage: `linear-gradient(0deg, rgba(23,22,15,0.035) 1px, transparent 1px),
          linear-gradient(90deg, rgba(23,22,15,0.035) 1px, transparent 1px),
          linear-gradient(0deg, rgba(255,255,255,0.6) 2px, transparent 2px),
          linear-gradient(90deg, rgba(255,255,255,0.6) 2px, transparent 2px)`,
        backgroundSize: '22px 22px, 22px 22px, 88px 88px, 88px 88px' }}>
        <svg width="100%" height="100%" viewBox="0 0 320 200" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0 }}>
          <polyline points="46,168 120,150 150,96 232,72 276,40" fill="none"
            stroke="var(--route)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" opacity="0.9" />
        </svg>
        <span style={{ position: 'absolute', left: 40, bottom: 150, width: 14, height: 14, borderRadius: '50%',
          background: '#fff', border: '4px solid var(--route)', transform: 'translate(-50%,50%)' }} />
        <span style={{ position: 'absolute', left: 276, top: 40, transform: 'translate(-50%,-90%)', color: 'var(--verdict-go)' }}>
          <Icon name="map-pin" size={30} strokeWidth={2.5} />
        </span>
        <span style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(255,255,255,0.85)',
          borderRadius: 6, padding: '3px 7px', fontSize: 10, color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)' }}>карта — заглушка</span>
      </div>
    );
  }

  function ProfBadge({ prof, size = 'md' }) {
    const p = PROF[prof];
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)',
        fontSize: size === 'sm' ? 12 : 13, fontWeight: 600 }}>
        <Icon name={p.icon} size={size === 'sm' ? 14 : 16} /> {p.label}
      </span>
    );
  }

  // ── job card (feed row) ───────────────────────────────────
  function JobCard({ job, onOpen }) {
    return (
      <Card interactive padding="md" onClick={onOpen} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <ProfBadge prof={job.prof} />
          <Verdict level={job.level} size="sm" />
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.01em' }}>{job.title}</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{job.addr}</div>
        </div>
        <div style={{ display: 'flex', gap: 20, paddingTop: 4, borderTop: '1px solid var(--border-subtle)' }}>
          <Metric label="Оплата" value={fmt(job.pay)} unit="₽" tone="brand" size="sm" />
          <Metric label="Дистанция" value={String(job.km).replace('.', ',')} unit="км" size="sm" />
          <Metric label="Время" value={job.min} unit="мин" size="sm" />
          <Metric label="Чистыми/ч" value={'₽' + fmt(job.perHour)} tone={toneFor(job.level)} size="sm" />
        </div>
      </Card>
    );
  }

  // ── FEED ──────────────────────────────────────────────────
  function FeedScreen({ online, setOnline, onOpen }) {
    const [filter, setFilter] = React.useState('all');
    const filtered = filter === 'all' ? JOBS : JOBS.filter((j) => j.prof === filter);
    const goodCount = JOBS.filter((j) => j.level === 'go').length;
    return (
      <ScreenShell>
        <TopBar
          title="Лента заказов"
          sub={`${goodCount} стоящих сейчас`}
          right={<IconButton aria-label="Уведомления" variant="ghost"><Icon name="bell" /></IconButton>}
        />
        <Main>
          <Card variant="raised" padding="md" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Сегодня заработано</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 600, color: 'var(--brand)', letterSpacing: '-0.01em' }}>₽{fmt(EARN.today)}</div>
            </div>
            <Switch label={online ? 'На смене' : 'Не на смене'} labelPosition="left" checked={online} onChange={(e) => setOnline(e.target.checked)} />
          </Card>

          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', margin: '0 -16px', padding: '2px 16px' }}>
            <Tag selected={filter === 'all'} onClick={() => setFilter('all')}>Все</Tag>
            {Object.keys(PROF).map((k) => (
              <Tag key={k} icon={<Icon name={PROF[k].icon} size={14} />} selected={filter === k} onClick={() => setFilter(k)}>{PROF[k].label}</Tag>
            ))}
          </div>

          {filtered.map((j) => <JobCard key={j.id} job={j} onOpen={() => onOpen(j.id)} />)}
        </Main>
      </ScreenShell>
    );
  }

  // ── JOB DETAIL ────────────────────────────────────────────
  function DetailScreen({ job, onBack, onTake }) {
    return (
      <ScreenShell>
        <TopBar title="Разбор поездки" back onBack={onBack} />
        <Main>
          <MapView height={168} />

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.01em' }}>{job.title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{job.addr}</div>
            </div>
            <ProfBadge prof={job.prof} />
          </div>

          <Verdict level={job.level} size="lg" reason={job.reason} />

          <div style={{ display: 'flex', gap: 20, justifyContent: 'space-between' }}>
            <Metric label="Оплата" value={fmt(job.pay)} unit="₽" tone="brand" size="md" />
            <Metric label="Дистанция" value={String(job.km).replace('.', ',')} unit="км" size="md" />
            <Metric label="Время" value={job.min} unit="мин" size="md" />
          </div>

          <Card padding="md" style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: 10 }}>Как посчитали</div>
            {job.steps.map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0',
                borderBottom: '1px solid var(--border-subtle)', fontSize: 14 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{s.k}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600,
                  color: s.v > 0 ? 'var(--verdict-go-text)' : s.v < 0 ? 'var(--verdict-skip-text)' : 'var(--text-tertiary)' }}>
                  {s.v > 0 ? '+' : ''}{fmt(s.v)} ₽
                </span>
              </div>
            ))}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: 12 }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Чистыми в час</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 24,
                color: job.level === 'skip' ? 'var(--verdict-skip-text)' : 'var(--brand)' }}>₽{fmt(job.perHour)}</span>
            </div>
          </Card>
        </Main>

        <div style={{ flex: 'none', padding: '12px 16px 28px', borderTop: '1px solid var(--border-default)',
          background: 'var(--color-surface)', display: 'flex', gap: 10 }}>
          <Button variant="secondary" size="lg" onClick={onBack}>Пропустить</Button>
          <Button variant={job.level === 'skip' ? 'secondary' : 'primary'} size="lg" fullWidth
            iconLeft={<Icon name="circle-check" size={20} />} onClick={() => onTake(job)}>Взять заказ</Button>
        </div>
      </ScreenShell>
    );
  }

  // ── ACTIVE TRIP ───────────────────────────────────────────
  function TripScreen({ job, onFinish }) {
    if (!job) {
      return (
        <ScreenShell>
          <TopBar title="В пути" />
          <Main>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', textAlign: 'center', gap: 12, color: 'var(--text-tertiary)', paddingTop: 80 }}>
              <Icon name="navigation" size={40} />
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)' }}>Сейчас ты никуда не едешь</div>
              <div style={{ fontSize: 14, maxWidth: 240 }}>Возьми стоящий заказ из ленты — и он появится здесь.</div>
            </div>
          </Main>
        </ScreenShell>
      );
    }
    return (
      <ScreenShell>
        <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
          <MapView height={520} radius={0} />
          <div style={{ position: 'absolute', top: 60, left: 16, right: 16 }}>
            <Card variant="raised" padding="md" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--brand-subtle)',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brand-active)' }}>
                <Icon name="corner-up-right" size={24} strokeWidth={2.25} />
              </span>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 600 }}>Через 400 м направо</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>на Тверскую · затем прямо 2 км</div>
              </div>
            </Card>
          </div>
          <div style={{ position: 'absolute', bottom: 12, right: 12 }}>
            <IconButton aria-label="Мой курс" variant="solid" round><Icon name="navigation" /></IconButton>
          </div>
        </div>
        <div style={{ flex: 'none', padding: '16px 16px 28px', borderTop: '1px solid var(--border-default)',
          background: 'var(--color-surface)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{job.title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{job.client} · {job.addr}</div>
            </div>
            <Metric label="Заработок" value={'₽' + fmt(job.pay)} tone="brand" size="md" />
          </div>
          <Button variant="primary" size="xl" fullWidth iconLeft={<Icon name="flag" size={20} />} onClick={onFinish}>
            Я на месте
          </Button>
        </div>
      </ScreenShell>
    );
  }

  // ── EARNINGS ──────────────────────────────────────────────
  function EarningsScreen() {
    const [period, setPeriod] = React.useState('week');
    const max = Math.max(...EARN.week.map((w) => w.v));
    return (
      <ScreenShell>
        <TopBar title="Смена" sub="Пятница, 5 июля" right={<IconButton aria-label="Календарь" variant="ghost"><Icon name="calendar" /></IconButton>} />
        <Main>
          <Card variant="raised" padding="lg" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Заработано сегодня</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 40, fontWeight: 600, color: 'var(--brand)', letterSpacing: '-0.02em', lineHeight: 1.05 }}>₽{fmt(EARN.today)}</div>
            </div>
            <div>
              <div style={{ height: 8, borderRadius: 999, background: 'var(--neutral-200)', overflow: 'hidden' }}>
                <div style={{ width: Math.round((EARN.today / EARN.goal) * 100) + '%', height: '100%', background: 'var(--brand)', borderRadius: 999 }} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>Цель на день — ₽{fmt(EARN.goal)}. Осталось ₽{fmt(EARN.goal - EARN.today)}.</div>
            </div>
            <div style={{ display: 'flex', gap: 24, paddingTop: 4 }}>
              <Metric label="Заказов" value={EARN.jobsDone} size="md" />
              <Metric label="Часов" value={String(EARN.hours).replace('.', ',')} size="md" />
              <Metric label="Чистыми/ч" value={'₽' + fmt(EARN.perHour)} tone="go" size="md" />
            </div>
          </Card>

          <Tabs variant="segmented" fullWidth value={period} onChange={setPeriod}
            items={[{ value: 'day', label: 'День' }, { value: 'week', label: 'Неделя' }, { value: 'month', label: 'Месяц' }]} />

          <Card padding="md">
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height: 140 }}>
              {EARN.week.map((w, i) => {
                const isToday = i === 4;
                return (
                  <div key={w.d} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, height: '100%', justifyContent: 'flex-end' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-tertiary)' }}>{Math.round(w.v / 1000)}к</div>
                    <div style={{ width: '100%', height: Math.round((w.v / max) * 96) + 'px',
                      background: isToday ? 'var(--brand)' : 'var(--green-100)', borderRadius: 6 }} />
                    <div style={{ fontSize: 11, color: isToday ? 'var(--text-primary)' : 'var(--text-tertiary)', fontWeight: isToday ? 700 : 500 }}>{w.d}</div>
                  </div>
                );
              })}
            </div>
          </Card>

          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginTop: 4 }}>Последние</div>
          {EARN.recent.map((r, i) => (
            <Card key={i} padding="sm" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Verdict level={r.level} size="sm" />
                <span style={{ fontSize: 14, fontWeight: 600 }}>{r.title}</span>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--brand)' }}>+₽{fmt(r.pay)}</span>
            </Card>
          ))}
        </Main>
      </ScreenShell>
    );
  }

  // ── PROFILE ───────────────────────────────────────────────
  function ProfileScreen() {
    return (
      <ScreenShell>
        <TopBar title="Профиль" right={<IconButton aria-label="Настройки" variant="ghost"><Icon name="settings" /></IconButton>} />
        <Main>
          <Card padding="md" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ width: 56, height: 56, borderRadius: '50%', background: 'var(--ink)', color: '#fff',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 20 }}>АК</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 18, fontWeight: 700 }}>Алексей К.</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                <ProfBadge prof="taxi" size="sm" />
                <Badge variant="warning" size="sm"><Icon name="star" size={12} /> 4,9</Badge>
              </div>
            </div>
          </Card>

          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginTop: 4 }}>Расчёт вердикта</div>
          <Card padding="md" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Select label="Транспорт" defaultValue="car" options={[
              { value: 'car', label: 'Авто · бензин' }, { value: 'bike', label: 'Велосипед' }, { value: 'foot', label: 'Пешком' }]} />
            <div style={{ display: 'flex', gap: 12 }}>
              <Input label="Цена бензина" suffix="₽/л" defaultValue="58" />
              <Input label="Минимум для «стоит»" suffix="₽/ч" defaultValue="500" />
            </div>
          </Card>

          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginTop: 4 }}>Что показывать</div>
          <Card padding="md" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Switch label="Считать бензин и износ" labelPosition="left" spread defaultChecked />
            <Switch label="Прятать заказы «не стоит»" labelPosition="left" spread />
            <div style={{ height: 1, background: 'var(--border-subtle)' }} />
            <Checkbox label="Только заказы рядом" description="В радиусе 5 км от меня" defaultChecked />
          </Card>

          <Button variant="ghost" fullWidth iconLeft={<Icon name="log-out" size={18} />} style={{ color: 'var(--danger-text)' }}>Выйти</Button>
        </Main>
      </ScreenShell>
    );
  }

  // ── APP shell ─────────────────────────────────────────────
  function App() {
    const IOSDevice = window.IOSDevice;
    const [tab, setTab] = React.useState('feed');
    const [view, setView] = React.useState({ screen: 'feed' });
    const [online, setOnline] = React.useState(true);
    const [trip, setTrip] = React.useState(null);
    const [toast, setToast] = React.useState(null);

    const flash = (t) => { setToast(t); clearTimeout(window.__vkT); window.__vkT = setTimeout(() => setToast(null), 3000); };

    const openJob = (id) => setView({ screen: 'detail', jobId: id });
    const backFeed = () => setView({ screen: 'feed' });
    const takeJob = (job) => { setTrip(job); setView({ screen: 'feed' }); setTab('trip'); flash({ variant: 'success', title: 'Заказ взят. Погнали!' }); };
    const finishTrip = (job) => { setTrip(null); setTab('earn'); flash({ variant: 'success', title: 'Готово. +₽' + fmt(job.pay) + ' на счёт' }); };

    const goTab = (k) => { setView({ screen: 'feed' }); setTab(k); };

    let body;
    if (view.screen === 'detail') {
      body = <DetailScreen job={JOBS.find((j) => j.id === view.jobId)} onBack={backFeed} onTake={takeJob} />;
    } else if (tab === 'feed') {
      body = <FeedScreen online={online} setOnline={setOnline} onOpen={openJob} />;
    } else if (tab === 'trip') {
      body = <TripScreen job={trip} onFinish={() => finishTrip(trip)} />;
    } else if (tab === 'earn') {
      body = <EarningsScreen />;
    } else {
      body = <ProfileScreen />;
    }

    const showTabs = view.screen !== 'detail';

    return (
      <IOSDevice width={402} height={874}>
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <div style={{ flex: 1, minHeight: 0 }}>{body}</div>
          {showTabs && <TabBar tab={tab} onTab={goTab} hasTrip={!!trip} />}
          {toast && (
            <div style={{ position: 'absolute', left: 16, right: 16, bottom: showTabs ? 96 : 40, zIndex: 80 }}>
              <Toast variant={toast.variant} title={toast.title} onClose={() => setToast(null)} />
            </div>
          )}
        </div>
      </IOSDevice>
    );
  }

  window.VKApp = App;
})();
