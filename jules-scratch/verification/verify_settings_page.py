from playwright.sync_api import Page, expect

def test_settings_page_improvements(page: Page):
    """
    This test verifies the UI improvements on the settings page.
    It checks for the new import/export buttons, the config file dropdown,
    and takes a screenshot to verify the responsive tabs and nested styling.
    """
    # 1. Arrange: Go to the settings page.
    # We assume the UI service is running on port 8000.
    page.goto("http://localhost:8000/settings")

    # 2. Assert: Check that the new controls are visible.
    expect(page.get_by_role("button", name="Export Settings")).to_be_visible()
    expect(page.get_by_role("button", name="Import Settings")).to_be_visible()
    expect(page.get_by_label("Load from config:")).to_be_visible()
    expect(page.get_by_role("button", name="Load")).to_be_visible()

    # 3. Assert: Check that the tabs are present.
    # We can check for at least one tab button.
    expect(page.locator(".tab-button")).to_have_count.greater_than(0)

    # 4. Screenshot: Capture the final result for visual verification.
    # This will show the layout of the new controls, the wrapping of the tabs,
    # and the visual styling of the nested settings.
    page.screenshot(path="jules-scratch/verification/settings_page.png")
