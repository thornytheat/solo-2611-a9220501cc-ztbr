import http from './http'
import type { BootstrapPayload, DictionaryPayload } from '../types/domain'

export async function fetchBootstrap(): Promise<BootstrapPayload> {
  const { data } = await http.get<BootstrapPayload>('/meta/bootstrap')
  return data
}

export async function fetchDictionary(): Promise<DictionaryPayload> {
  const { data } = await http.get<DictionaryPayload>('/meta/dictionary')
  return data
}
