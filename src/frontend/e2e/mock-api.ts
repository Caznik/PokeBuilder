import type { Page } from '@playwright/test'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { join, dirname } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))

function loadFixture(name: string): unknown {
  return JSON.parse(readFileSync(join(__dirname, 'fixtures', name), 'utf-8'))
}

const pokemonListFixture = loadFixture('pokemon-list.json')
const pokemonDetailFixture = loadFixture('pokemon-detail.json')
const competitiveSetsFixture = loadFixture('competitive-sets.json')
const scoreResponseFixture = loadFixture('score-response.json')
const savedTeamsListFixture = loadFixture('saved-teams-list.json')
const savedTeamDetailFixture = loadFixture('saved-team-detail.json') as Record<string, unknown>

function json(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

export async function mockAllApis(page: Page): Promise<void> {
  // Types list
  await page.route(
    (url) => url.pathname === '/api/types/',
    (route) => route.fulfill(json([{ id: 13, name: 'electric' }, { id: 10, name: 'fire' }]))
  )

  // Pokemon list (with optional query params)
  await page.route(
    (url) => url.pathname === '/api/pokemon/',
    (route) => route.fulfill(json(pokemonListFixture))
  )

  // Pokemon by name
  await page.route(
    (url) => url.pathname.startsWith('/api/pokemon/name/'),
    (route) => route.fulfill(json(pokemonDetailFixture))
  )

  // Competitive sets
  await page.route(
    (url) => url.pathname.startsWith('/api/competitive-sets/'),
    (route) => route.fulfill(json(competitiveSetsFixture))
  )

  // Team score
  await page.route(
    (url) => url.pathname === '/api/team/score',
    (route) => route.fulfill(json(scoreResponseFixture))
  )

  // Saved teams — distinguish GET list vs POST save
  await page.route(
    (url) => url.pathname === '/api/saved-teams/',
    async (route) => {
      if (route.request().method() === 'POST') {
        route.fulfill(json({ ...savedTeamDetailFixture, id: 99 }))
      } else {
        route.fulfill(json(savedTeamsListFixture))
      }
    }
  )

  // Saved team detail by ID
  await page.route(
    (url) => /^\/api\/saved-teams\/\d+$/.test(url.pathname),
    (route) => route.fulfill(json(savedTeamDetailFixture))
  )

  // Pokemon moves
  await page.route(
    (url) => url.pathname.startsWith('/api/moves/pokemon/'),
    (route) => route.fulfill(json({ pokemon_id: 25, pokemon_name: 'pikachu', moves: [] }))
  )
}
