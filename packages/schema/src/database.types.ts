export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: '14.5'
  }
  public: {
    Tables: {
      contribution_grants: {
        Row: {
          accepted_at: string
          attribution_name: string
          contributor_id: string
          data_license: string
          id: string
          photo_license: string
          terms_version: string
        }
        Insert: {
          accepted_at: string
          attribution_name: string
          contributor_id: string
          data_license?: string
          id?: string
          photo_license?: string
          terms_version: string
        }
        Update: {
          accepted_at?: string
          attribution_name?: string
          contributor_id?: string
          data_license?: string
          id?: string
          photo_license?: string
          terms_version?: string
        }
        Relationships: [
          {
            foreignKeyName: 'contribution_grants_contributor_id_fkey'
            columns: ['contributor_id']
            isOneToOne: false
            referencedRelation: 'contributors'
            referencedColumns: ['id']
          },
        ]
      }
      contributors: {
        Row: {
          auth_uid: string | null
          created_at: string
          handle: string
          id: string
          precise_location_optin: boolean
          reputation: number
        }
        Insert: {
          auth_uid?: string | null
          created_at?: string
          handle: string
          id?: string
          precise_location_optin?: boolean
          reputation?: number
        }
        Update: {
          auth_uid?: string | null
          created_at?: string
          handle?: string
          id?: string
          precise_location_optin?: boolean
          reputation?: number
        }
        Relationships: []
      }
      gold_labels: {
        Row: {
          depth_bottom_cm: number
          depth_top_cm: number
          document_ref: string | null
          id: string
          lab_name: string
          method: string | null
          property: string
          submission_id: string
          uncertainty: number | null
          unit: string
          value: number
          verified_by: string | null
        }
        Insert: {
          depth_bottom_cm: number
          depth_top_cm: number
          document_ref?: string | null
          id?: string
          lab_name: string
          method?: string | null
          property: string
          submission_id: string
          uncertainty?: number | null
          unit: string
          value: number
          verified_by?: string | null
        }
        Update: {
          depth_bottom_cm?: number
          depth_top_cm?: number
          document_ref?: string | null
          id?: string
          lab_name?: string
          method?: string | null
          property?: string
          submission_id?: string
          uncertainty?: number | null
          unit?: string
          value?: number
          verified_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: 'gold_labels_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'public_submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'gold_labels_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      h3_cells: {
        Row: {
          acquisition_score: number | null
          h3_index: string
          model_disagreement: number | null
          n_gold: number
          n_submissions: number
          prior_uncertainty: number | null
          updated_at: string
        }
        Insert: {
          acquisition_score?: number | null
          h3_index: string
          model_disagreement?: number | null
          n_gold?: number
          n_submissions?: number
          prior_uncertainty?: number | null
          updated_at?: string
        }
        Update: {
          acquisition_score?: number | null
          h3_index?: string
          model_disagreement?: number | null
          n_gold?: number
          n_submissions?: number
          prior_uncertainty?: number | null
          updated_at?: string
        }
        Relationships: []
      }
      photos: {
        Row: {
          camera_metadata_private: Json | null
          card_color_correction: Json | null
          card_detected: boolean | null
          id: string
          sharpness_score: number | null
          shot_type: string
          storage_path: string
          submission_id: string
        }
        Insert: {
          camera_metadata_private?: Json | null
          card_color_correction?: Json | null
          card_detected?: boolean | null
          id?: string
          sharpness_score?: number | null
          shot_type: string
          storage_path: string
          submission_id: string
        }
        Update: {
          camera_metadata_private?: Json | null
          card_color_correction?: Json | null
          card_detected?: boolean | null
          id?: string
          sharpness_score?: number | null
          shot_type?: string
          storage_path?: string
          submission_id?: string
        }
        Relationships: [
          {
            foreignKeyName: 'photos_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'public_submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'photos_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      predictions: {
        Row: {
          basis: string
          ci_hi: number
          ci_lo: number
          id: string
          model_version: string
          property: string
          submission_id: string
          unit: string
          value: number
        }
        Insert: {
          basis: string
          ci_hi: number
          ci_lo: number
          id?: string
          model_version: string
          property: string
          submission_id: string
          unit: string
          value: number
        }
        Update: {
          basis?: string
          ci_hi?: number
          ci_lo?: number
          id?: string
          model_version?: string
          property?: string
          submission_id?: string
          unit?: string
          value?: number
        }
        Relationships: [
          {
            foreignKeyName: 'predictions_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'public_submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'predictions_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      prior_jobs: {
        Row: {
          attempts: number
          completed_at: string | null
          last_error: string | null
          started_at: string | null
          status: string
          submission_id: string
          updated_at: string
        }
        Insert: {
          attempts?: number
          completed_at?: string | null
          last_error?: string | null
          started_at?: string | null
          status?: string
          submission_id: string
          updated_at?: string
        }
        Update: {
          attempts?: number
          completed_at?: string | null
          last_error?: string | null
          started_at?: string | null
          status?: string
          submission_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: 'prior_jobs_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: true
            referencedRelation: 'public_submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'prior_jobs_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: true
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      priors: {
        Row: {
          depth_bottom_cm: number
          depth_top_cm: number
          property: string
          retrieved_at: string
          source: string
          submission_id: string
          uncertainty_hi: number | null
          uncertainty_lo: number | null
          unit: string
          value: number | null
        }
        Insert: {
          depth_bottom_cm: number
          depth_top_cm: number
          property: string
          retrieved_at?: string
          source: string
          submission_id: string
          uncertainty_hi?: number | null
          uncertainty_lo?: number | null
          unit: string
          value?: number | null
        }
        Update: {
          depth_bottom_cm?: number
          depth_top_cm?: number
          property?: string
          retrieved_at?: string
          source?: string
          submission_id?: string
          uncertainty_hi?: number | null
          uncertainty_lo?: number | null
          unit?: string
          value?: number | null
        }
        Relationships: [
          {
            foreignKeyName: 'priors_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'public_submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'priors_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      qa_events: {
        Row: {
          check_name: string
          model_version: string | null
          passed: boolean
          score: number | null
          submission_id: string
        }
        Insert: {
          check_name: string
          model_version?: string | null
          passed: boolean
          score?: number | null
          submission_id: string
        }
        Update: {
          check_name?: string
          model_version?: string | null
          passed?: boolean
          score?: number | null
          submission_id?: string
        }
        Relationships: [
          {
            foreignKeyName: 'qa_events_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'public_submissions'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'qa_events_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      submissions: {
        Row: {
          captured_at: string
          contributor_id: string
          device_model: string | null
          disturbed: boolean | null
          elevation: number | null
          geom_precise: unknown
          grant_id: string
          h3_r6: string
          h3_r8: string
          id: string
          land_cover: string | null
          precip_flag: boolean | null
          status: string
          surface_condition: string | null
        }
        Insert: {
          captured_at: string
          contributor_id: string
          device_model?: string | null
          disturbed?: boolean | null
          elevation?: number | null
          geom_precise: unknown
          grant_id: string
          h3_r6: string
          h3_r8: string
          id?: string
          land_cover?: string | null
          precip_flag?: boolean | null
          status?: string
          surface_condition?: string | null
        }
        Update: {
          captured_at?: string
          contributor_id?: string
          device_model?: string | null
          disturbed?: boolean | null
          elevation?: number | null
          geom_precise?: unknown
          grant_id?: string
          h3_r6?: string
          h3_r8?: string
          id?: string
          land_cover?: string | null
          precip_flag?: boolean | null
          status?: string
          surface_condition?: string | null
        }
        Relationships: [
          {
            foreignKeyName: 'submissions_contributor_id_fkey'
            columns: ['contributor_id']
            isOneToOne: false
            referencedRelation: 'contributors'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'submissions_grant_owner_fkey'
            columns: ['grant_id', 'contributor_id']
            isOneToOne: false
            referencedRelation: 'contribution_grants'
            referencedColumns: ['id', 'contributor_id']
          },
        ]
      }
    }
    Views: {
      public_submissions: {
        Row: {
          captured_at: string | null
          disturbed: boolean | null
          elevation: number | null
          h3_r6: string | null
          h3_r8: string | null
          id: string | null
          land_cover: string | null
          precip_flag: boolean | null
          status: string | null
          surface_condition: string | null
        }
        Insert: {
          captured_at?: string | null
          disturbed?: boolean | null
          elevation?: number | null
          h3_r6?: string | null
          h3_r8?: string | null
          id?: string | null
          land_cover?: string | null
          precip_flag?: boolean | null
          status?: string | null
          surface_condition?: string | null
        }
        Update: {
          captured_at?: string | null
          disturbed?: boolean | null
          elevation?: number | null
          h3_r6?: string | null
          h3_r8?: string | null
          id?: string | null
          land_cover?: string | null
          precip_flag?: boolean | null
          status?: string | null
          surface_condition?: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      current_contributor_id: { Args: never; Returns: string }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, '__InternalSupabase'>

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, 'public'>]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema['Tables'] & DefaultSchema['Views'])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Views'])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Views'])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema['Tables'] &
        DefaultSchema['Views'])
    ? (DefaultSchema['Tables'] &
        DefaultSchema['Views'])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema['Tables'] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables']
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema['Tables']
    ? DefaultSchema['Tables'][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema['Tables'] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables']
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema['Tables']
    ? DefaultSchema['Tables'][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    keyof DefaultSchema['Enums'] | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions['schema']]['Enums']
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions['schema']]['Enums'][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema['Enums']
    ? DefaultSchema['Enums'][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema['CompositeTypes']
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions['schema']]['CompositeTypes']
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions['schema']]['CompositeTypes'][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema['CompositeTypes']
    ? DefaultSchema['CompositeTypes'][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
