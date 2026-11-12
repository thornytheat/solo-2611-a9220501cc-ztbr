export type UserRole = 'admin' | 'analyst' | 'client'

export interface User {
  id: string
  email: string
  display_name: string
  role: UserRole
  brand_key: string | null
  brand_label: string
  permissions: string[]
  scope: string
  is_active: boolean
}

export interface LoginResult {
  access_token: string
  token: string
  token_type: string
  user: User
}
