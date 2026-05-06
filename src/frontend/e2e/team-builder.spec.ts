import { test, expect, type Page } from '@playwright/test'
import { mockAllApis } from './mock-api'

test.beforeEach(async ({ page }) => {
  await mockAllApis(page)
})

async function fillOneSlot(page: Page) {
  // Click the first visible "+ Add Pokémon" button
  const addBtn = page.getByText('+ Add Pokémon').first()
  await addBtn.click()

  // Wait for the picker browse step to show pikachu and click it
  const pikachuBtn = page.getByRole('button', { name: /pikachu/i }).first()
  await expect(pikachuBtn).toBeVisible()
  await pikachuBtn.click()

  // Wait for the detail step to show Confirm and click it
  // The fixture has exactly 1 set so it auto-selects, enabling Confirm
  const confirmBtn = page.getByRole('button', { name: /confirm/i })
  await expect(confirmBtn).toBeEnabled()
  await confirmBtn.click()

  // Wait for the picker to close (Confirm button disappears)
  await expect(confirmBtn).not.toBeVisible()
}

test('score button is disabled with empty team', async ({ page }) => {
  await page.goto('/teams')

  // Wait for the page to be ready (6 Add Pokémon buttons should appear)
  await expect(page.getByText('+ Add Pokémon').first()).toBeVisible()

  const scoreBtn = page.getByRole('button', { name: /score team/i })
  await expect(scoreBtn).toBeDisabled()
})

test('score button enables after 6 slots filled', async ({ page }) => {
  await page.goto('/teams')

  await expect(page.getByText('+ Add Pokémon').first()).toBeVisible()

  for (let i = 0; i < 6; i++) {
    await fillOneSlot(page)
  }

  const scoreBtn = page.getByRole('button', { name: /score team/i })
  await expect(scoreBtn).toBeEnabled()
})

test('full flow: fill team, score, save', async ({ page }) => {
  await page.goto('/teams')

  await expect(page.getByText('+ Add Pokémon').first()).toBeVisible()

  // Fill all 6 slots
  for (let i = 0; i < 6; i++) {
    await fillOneSlot(page)
  }

  // Click Score Team
  const scoreBtn = page.getByRole('button', { name: /score team/i })
  await expect(scoreBtn).toBeEnabled()
  await scoreBtn.click()

  // Wait for score result to appear
  await expect(page.getByText('Team Score')).toBeVisible()

  // Type a team name and save
  const nameInput = page.getByPlaceholder('Team name...')
  await expect(nameInput).toBeVisible()
  await nameInput.fill('My E2E Team')

  const saveBtn = page.getByRole('button', { name: /^save$/i })
  await expect(saveBtn).toBeEnabled()
  await saveBtn.click()

  // Confirm save success
  await expect(page.getByText('Team saved!')).toBeVisible()
})
