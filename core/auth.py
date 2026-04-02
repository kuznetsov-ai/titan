"""Authentication module — handles login/password flows via Playwright."""

from playwright.async_api import BrowserContext, Page

from config.loader import RoleConfig, SystemConfig


async def login(page: Page, config: SystemConfig, role: RoleConfig) -> bool:
    """Perform login for a given role. Returns True on success."""
    login_url = config.base_url.rstrip("/") + config.auth.login_url
    await page.goto(login_url, wait_until="networkidle", timeout=config.browser.timeout)

    # Fill credentials
    username_input = page.locator(config.auth.username_selector).first
    password_input = page.locator(config.auth.password_selector).first
    submit_btn = page.locator(config.auth.submit_selector).first

    await username_input.fill(role.username)
    await password_input.fill(role.password)
    await submit_btn.click()

    # Wait for navigation after login
    try:
        await page.wait_for_load_state("networkidle", timeout=config.browser.timeout)
    except Exception:
        pass

    # Extra wait for SPA redirect
    import asyncio
    await asyncio.sleep(2)

    # Check if login succeeded by looking for auth indicators
    # After successful login: sidebar with user email visible, or auth page gone
    current_url = page.url.lower()

    # Still on /auth page with form = login failed
    if "/auth" in current_url and "redirecturl" in current_url:
        return False

    # Check for authenticated UI elements (user email, logout button)
    logout_btn = page.locator("text='Logout', text='logout', [class*='logout']")
    if await logout_btn.count() > 0:
        return True

    # Fallback: if URL changed from auth page, consider it success
    return "/auth?" not in current_url


async def create_authenticated_context(
    browser, config: SystemConfig, role: RoleConfig
) -> BrowserContext:
    """Create a new browser context and authenticate the given role."""
    context = await browser.new_context(
        viewport={
            "width": config.browser.viewport_width,
            "height": config.browser.viewport_height,
        },
        ignore_https_errors=config.browser.ignore_https_errors,
    )
    page = await context.new_page()
    success = await login(page, config, role)
    if not success:
        await context.close()
        raise RuntimeError(f"Login failed for role '{role.name}' ({role.username})")
    return context
