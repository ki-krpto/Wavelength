(function () {
  // ─── Mirror Detection ────────────────────────────────────────────────────────
  // Add any mirror hostnames here. The main site will NOT show the banner.
  const MIRROR_HOSTS = [
"wavelength.rip",
"wavelength-real.pages.dev",
  ];

  const MAIN_SITE_HOST = "wavelength-8vk.pages.dev";
  const MAIN_SITE_URL  = "https://wavelength-8vk.pages.dev";

  const currentHost = location.hostname;

  // Show banner if:
  //  - current host is explicitly listed as a mirror, OR
  //  - current host is NOT the main site (and not localhost for dev)
  const isDev    = currentHost === "localhost" || currentHost === "127.0.0.1";
  const isMain   = currentHost === MAIN_SITE_HOST;
  const isMirror = !isDev && !isMain;

  if (!isMirror) return;

  // ─── Banner injection ────────────────────────────────────────────────────────
  const STORAGE_KEY = "wl-mirror-banner-dismissed";

  // Don't re-show if user already closed it this session
  if (sessionStorage.getItem(STORAGE_KEY)) return;

  const style = document.createElement("style");
  style.textContent = `
    #wl-mirror-banner {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 99999;
      background: #000080;
      color: #ffffff;
      font-family: inherit;
      font-size: 12px;
      padding: 7px 40px 7px 12px;
      border-bottom: 2px solid #ffffff;
      display: flex;
      align-items: center;
      gap: 8px;
      line-height: 1.4;
      box-shadow: 0 2px 0 #000;
    }
    #wl-mirror-banner a {
      color: #ffff00;
      text-decoration: underline;
    }
    #wl-mirror-banner a:hover {
      color: #ffffff;
    }
    #wl-mirror-banner-close {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      background: #c0c0c0;
      color: #000000;
      border: 2px outset #ffffff;
      font-family: inherit;
      font-size: 11px;
      padding: 1px 5px;
      cursor: pointer;
      line-height: 1.2;
    }
    #wl-mirror-banner-close:active {
      border-style: inset;
    }
    /* Push page content down so banner doesn't overlap */
    body.wl-mirror-offset {
      padding-top: 36px;
    }
  `;
  document.head.appendChild(style);

  const banner = document.createElement("div");
  banner.id = "wl-mirror-banner";
  banner.setAttribute("role", "status");
  banner.innerHTML = `
    <span>&#9432;</span>
    <span>
      This is a site mirror! This updates every 7 minutes so new updates might take a bit to show here.
      Our main site is <a href="${MAIN_SITE_URL}" target="_blank" rel="noopener">${MAIN_SITE_HOST}</a>. <3
    </span>
    <button id="wl-mirror-banner-close" aria-label="Dismiss banner">[ x ]</button>
  `;

  function insertBanner() {
    document.body.insertAdjacentElement("afterbegin", banner);
    document.body.classList.add("wl-mirror-offset");
  }

  // Insert as soon as body is available
  if (document.body) {
    insertBanner();
  } else {
    document.addEventListener("DOMContentLoaded", insertBanner);
  }

  document.addEventListener("click", function (e) {
    if (e.target && e.target.id === "wl-mirror-banner-close") {
      banner.remove();
      document.body.classList.remove("wl-mirror-offset");
      sessionStorage.setItem(STORAGE_KEY, "1");
    }
  });
})();