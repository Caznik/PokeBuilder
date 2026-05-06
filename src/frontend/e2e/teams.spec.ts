import { test, expect } from '@playwright/test'
import { mockAllApis } from './mock-api'

test.beforeEach(async ({ page }) => {
  await mockAllApis(page)
})

test('saved tab shows team list', async ({ page }) => {
  await page.goto('/teams?tab=saved')
  await expect(page.getByText('My Test Team')).toBeVisible()
})

test('navigate from saved list to team detail', async ({ page }) => {
  await page.goto('/teams?tab=saved')
  await expect(page.getByText('My Test Team')).toBeVisible()
  // The team card is a div with onClick -> navigate; click the team name text
  await page.getByText('My Test Team').first().click()
  await page.waitForURL('/teams/1')
  await expect(page.getByRole('heading', { name: 'My Test Team' })).toBeVisible()
})

test('team detail shows 6 member slots', async ({ page }) => {
  await page.goto('/teams/1')
  // Each member slot is a clickable div with a pokemon name; the detail fixture has 6 members
  // Each slot renders a div with the pokemon name text and a sprite image
  // The grid container holds exactly 6 slot divs — locate by the slot's pokemon name images
  const slots = page.locator('div[style*="border-radius: 8px"]')
  await expect(slots).toHaveCount(6)
})
