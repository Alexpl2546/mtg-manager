# Continuation prompt: APlot Secure UI

Рабочая директория: `D:\VPN\vpn-proxy-manager-web`

Репозиторий: `https://github.com/Alexpl2546/vpn-proxy-manager-web.git`

Актуальный commit: `63702e7` (`Apply APlot Secure brand redesign`), ветка `main`, изменения запушены в `origin/main`.

Контекст:
- Это Next.js 16 / React 19 / Tailwind CSS 4 приложение личного кабинета.
- Последняя задача была визуально переработать интерфейс под приложенный логотип APlot Secure.
- UX и бизнес-логика не должны меняться, только визуальный слой.

Что уже сделано:
- В `src/app/globals.css` создана дизайн-система на основе логотипа: dark navy фон, blue/cyan акценты, мягкое glow, единые radius/shadow tokens.
- Обновлены базовые UI-компоненты: `button`, `card`, `input`, `badge`, `progress`.
- Обновлены app shell, auth-экраны, subscription/pricing, connection cards, QR, device icons.
- Бренд в UI и metadata заменён на `APlot Secure`.
- Исправлена compact-раскладка карточек подключений на главной, чтобы кнопки и бейджи не накладывались.

Проверки уже проходили:
- `npm run lint`
- `npm run build`
- Browser check desktop/mobile: нет console errors, нет горизонтального overflow, брендовые элементы отображаются.

Как продолжить:
1. `cd D:\VPN\vpn-proxy-manager-web`
2. Если зависимостей нет: `npm install`
3. Запуск: `npm run dev`
4. Открыть: `http://localhost:3000`

Важно:
- Не возвращать старую палитру NetConnect/фиолетовые акценты.
- Не добавлять hacker/VPN cliché стилистику.
- Сохранять премиальный SaaS-тон: Stripe / Proton / Linear / Tailscale.
- Если продолжать визуальный polish, начинать с browser review страниц `/`, `/connections`, `/subscription`, `/login`, `/register`.
