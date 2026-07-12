/* Визиторкрут — mock data for the app UI kit (window.VK) */
window.VK = {
  professions: {
    taxi:    { label: 'Такси',  icon: 'car-front' },
    courier: { label: 'Курьер', icon: 'package' },
    doc:     { label: 'Врач',   icon: 'stethoscope' },
    master:  { label: 'Мастер', icon: 'wrench' },
  },

  jobs: [
    {
      id: 'j1', prof: 'doc', level: 'go',
      title: 'Вызов на дом', addr: 'Пресня, ул. 1905 года, 8',
      pay: 3200, km: 4.1, min: 15, perHour: 980, client: 'Ирина М.',
      reason: 'Рядом и дорого — бери не думая.',
      steps: [
        { k: 'Оплата вызова', v: 3200, kind: 'plus' },
        { k: 'Бензин 4 км', v: -60, kind: 'minus' },
        { k: 'Время в пути 15 мин', v: -140, kind: 'minus' },
      ],
    },
    {
      id: 'j2', prof: 'taxi', level: 'go',
      title: 'До Шереметьево', addr: 'Тверская, 12 → SVO',
      pay: 2480, km: 38, min: 44, perHour: 640, client: 'Пассажир',
      reason: 'Загород без пробок — ₽640/ч чистыми.',
      steps: [
        { k: 'Тариф', v: 2480, kind: 'plus' },
        { k: 'Бензин 38 км', v: -420, kind: 'minus' },
        { k: 'Время в пути 44 мин', v: -410, kind: 'minus' },
      ],
    },
    {
      id: 'j3', prof: 'courier', level: 'go',
      title: 'Еда · 2 заказа рядом', addr: 'Патрики, два адреса по пути',
      pay: 560, km: 2.3, min: 12, perHour: 720, client: '2 клиента',
      reason: 'Два заказа по пути — быстрые деньги.',
      steps: [
        { k: 'Два заказа', v: 560, kind: 'plus' },
        { k: 'Самокат', v: 0, kind: 'minus' },
        { k: 'Время 12 мин', v: -120, kind: 'minus' },
      ],
    },
    {
      id: 'j4', prof: 'taxi', level: 'edge',
      title: 'По городу', addr: 'Арбат → Москва-Сити',
      pay: 640, km: 5.8, min: 26, perHour: 420, client: 'Пассажир',
      reason: 'Днём Садовое стоит — 50 на 50.',
      steps: [
        { k: 'Тариф', v: 640, kind: 'plus' },
        { k: 'Бензин 6 км', v: -70, kind: 'minus' },
        { k: 'Время в пробке 26 мин', v: -290, kind: 'minus' },
      ],
    },
    {
      id: 'j5', prof: 'courier', level: 'edge',
      title: 'Посылка, Китай-город', addr: '3 этажа без лифта',
      pay: 420, km: 6.2, min: 34, perHour: 310, client: 'Пункт выдачи',
      reason: 'Подъёмы без лифта съедят время.',
      steps: [
        { k: 'Доставка', v: 420, kind: 'plus' },
        { k: 'Самокат 6 км', v: -20, kind: 'minus' },
        { k: 'Время 34 мин', v: -260, kind: 'minus' },
      ],
    },
    {
      id: 'j6', prof: 'master', level: 'skip',
      title: 'Сборка шкафа', addr: 'Южное Бутово, далеко',
      pay: 1500, km: 22, min: 71, perHour: 280, client: 'Сергей П.',
      reason: 'Далеко и пробки — уйдёшь в минус по времени.',
      steps: [
        { k: 'Работа', v: 1500, kind: 'plus' },
        { k: 'Бензин 22 км + обратно', v: -480, kind: 'minus' },
        { k: 'Время в пути 71 мин', v: -660, kind: 'minus' },
      ],
    },
  ],

  earnings: {
    today: 4820,
    jobsDone: 7,
    hours: 5.5,
    perHour: 876,
    goal: 6000,
    week: [
      { d: 'Пн', v: 3200 }, { d: 'Вт', v: 5100 }, { d: 'Ср', v: 4200 },
      { d: 'Чт', v: 6100 }, { d: 'Пт', v: 4820 }, { d: 'Сб', v: 7300 },
      { d: 'Вс', v: 1900 },
    ],
    recent: [
      { title: 'Вызов на дом · Пресня', pay: 3060, level: 'go' },
      { title: 'До Внуково', pay: 2140, level: 'go' },
      { title: 'Еда · Патрики', pay: 320, level: 'edge' },
    ],
  },
};
