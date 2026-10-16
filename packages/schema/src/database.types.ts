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
      actors: {
        Row: {
          contributor_id: string | null
          created_at: string
          id: string
          kind: string
          model_family: string | null
          model_version: string | null
          operator_id: string | null
          status: string
        }
        Insert: {
          contributor_id?: string | null
          created_at?: string
          id?: string
          kind: string
          model_family?: string | null
          model_version?: string | null
          operator_id?: string | null
          status?: string
        }
        Update: {
          contributor_id?: string | null
          created_at?: string
          id?: string
          kind?: string
          model_family?: string | null
          model_version?: string | null
          operator_id?: string | null
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: 'actors_contributor_id_fkey'
            columns: ['contributor_id']
            isOneToOne: false
            referencedRelation: 'contributors'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'actors_operator_id_fkey'
            columns: ['operator_id']
            isOneToOne: false
            referencedRelation: 'actors'
            referencedColumns: ['id']
          },
        ]
      }
      attribution_reviews: {
        Row: {
          attribution_name: string
          contributor_id: string
          decision: string
          note: string | null
          reviewed_at: string
          reviewer: string
        }
        Insert: {
          attribution_name: string
          contributor_id: string
          decision: string
          note?: string | null
          reviewed_at?: string
          reviewer: string
        }
        Update: {
          attribution_name?: string
          contributor_id?: string
          decision?: string
          note?: string | null
          reviewed_at?: string
          reviewer?: string
        }
        Relationships: [
          {
            foreignKeyName: 'attribution_reviews_contributor_id_fkey'
            columns: ['contributor_id']
            isOneToOne: false
            referencedRelation: 'contributors'
            referencedColumns: ['id']
          },
        ]
      }
      contribution_grants: {
        Row: {
          accepted_at: string
          attribution_name: string
          contributor_id: string
          data_license: string
          id: string
          photo_license: string
          received_at: string | null
          terms_version: string
        }
        Insert: {
          accepted_at: string
          attribution_name: string
          contributor_id: string
          data_license?: string
          id?: string
          photo_license?: string
          received_at?: string | null
          terms_version: string
        }
        Update: {
          accepted_at?: string
          attribution_name?: string
          contributor_id?: string
          data_license?: string
          id?: string
          photo_license?: string
          received_at?: string | null
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
          {
            foreignKeyName: 'contribution_grants_terms_version_fkey'
            columns: ['terms_version']
            isOneToOne: false
            referencedRelation: 'terms_versions'
            referencedColumns: ['version']
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
      deletion_requests: {
        Row: {
          attempts: number
          claimed_at: string | null
          completed_at: string | null
          contributor_id: string
          id: string
          kind: string
          last_error: string | null
          not_before: string | null
          requested_at: string
          status: string
        }
        Insert: {
          attempts?: number
          claimed_at?: string | null
          completed_at?: string | null
          contributor_id: string
          id?: string
          kind: string
          last_error?: string | null
          not_before?: string | null
          requested_at?: string
          status?: string
        }
        Update: {
          attempts?: number
          claimed_at?: string | null
          completed_at?: string | null
          contributor_id?: string
          id?: string
          kind?: string
          last_error?: string | null
          not_before?: string | null
          requested_at?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: 'deletion_requests_contributor_id_fkey'
            columns: ['contributor_id']
            isOneToOne: false
            referencedRelation: 'contributors'
            referencedColumns: ['id']
          },
        ]
      }
      gold_labels: {
        Row: {
          depth_bottom_cm: number
          depth_top_cm: number
          document_ref: string | null
          holdout: boolean
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
          holdout?: boolean
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
          holdout?: boolean
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
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      h3_cells: {
        Row: {
          acquisition_score: number | null
          h3_index: string
          latest_submission_date: string | null
          model_disagreement: number | null
          n_contributors: number
          n_gold: number
          n_submissions: number
          prior_uncertainty: number | null
          resolution: number
          updated_at: string
        }
        Insert: {
          acquisition_score?: number | null
          h3_index: string
          latest_submission_date?: string | null
          model_disagreement?: number | null
          n_contributors: number
          n_gold?: number
          n_submissions?: number
          prior_uncertainty?: number | null
          resolution: number
          updated_at?: string
        }
        Update: {
          acquisition_score?: number | null
          h3_index?: string
          latest_submission_date?: string | null
          model_disagreement?: number | null
          n_contributors?: number
          n_gold?: number
          n_submissions?: number
          prior_uncertainty?: number | null
          resolution?: number
          updated_at?: string
        }
        Relationships: []
      }
      grant_withdrawals: {
        Row: {
          grant_id: string
          reason: string
          request_id: string | null
          withdrawn_at: string
        }
        Insert: {
          grant_id: string
          reason: string
          request_id?: string | null
          withdrawn_at?: string
        }
        Update: {
          grant_id?: string
          reason?: string
          request_id?: string | null
          withdrawn_at?: string
        }
        Relationships: [
          {
            foreignKeyName: 'grant_withdrawals_grant_id_fkey'
            columns: ['grant_id']
            isOneToOne: false
            referencedRelation: 'contribution_grants'
            referencedColumns: ['id']
          },
          {
            foreignKeyName: 'grant_withdrawals_request_id_fkey'
            columns: ['request_id']
            isOneToOne: false
            referencedRelation: 'deletion_requests'
            referencedColumns: ['id']
          },
        ]
      }
      photos: {
        Row: {
          calibration_status: string | null
          camera_metadata_private: Json | null
          capture_evidence_private: Json | null
          card_color_correction: Json | null
          card_detected: boolean | null
          id: string
          perceptual_hash: string | null
          provenance_tier: number
          qa_status: string | null
          sharpness_score: number | null
          shot_type: string
          storage_path: string
          submission_id: string
        }
        Insert: {
          calibration_status?: string | null
          camera_metadata_private?: Json | null
          capture_evidence_private?: Json | null
          card_color_correction?: Json | null
          card_detected?: boolean | null
          id?: string
          perceptual_hash?: string | null
          provenance_tier?: number
          qa_status?: string | null
          sharpness_score?: number | null
          shot_type: string
          storage_path: string
          submission_id: string
        }
        Update: {
          calibration_status?: string | null
          camera_metadata_private?: Json | null
          capture_evidence_private?: Json | null
          card_color_correction?: Json | null
          card_detected?: boolean | null
          id?: string
          perceptual_hash?: string | null
          provenance_tier?: number
          qa_status?: string | null
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
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      prior_cell_cache: {
        Row: {
          h3_r9: string
          payload: Json
          retrieved_at: string
          source: string
        }
        Insert: {
          h3_r9: string
          payload: Json
          retrieved_at?: string
          source: string
        }
        Update: {
          h3_r9?: string
          payload?: Json
          retrieved_at?: string
          source?: string
        }
        Relationships: []
      }
      prior_jobs: {
        Row: {
          attempts: number
          completed_at: string | null
          empty_sources: string[]
          last_error: string | null
          started_at: string | null
          status: string
          submission_id: string
          updated_at: string
        }
        Insert: {
          attempts?: number
          completed_at?: string | null
          empty_sources?: string[]
          last_error?: string | null
          started_at?: string | null
          status?: string
          submission_id: string
          updated_at?: string
        }
        Update: {
          attempts?: number
          completed_at?: string | null
          empty_sources?: string[]
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
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      qa_events: {
        Row: {
          check_name: string
          model_version: string
          passed: boolean
          score: number | null
          submission_id: string
        }
        Insert: {
          check_name: string
          model_version?: string
          passed: boolean
          score?: number | null
          submission_id: string
        }
        Update: {
          check_name?: string
          model_version?: string
          passed?: boolean
          score?: number | null
          submission_id?: string
        }
        Relationships: [
          {
            foreignKeyName: 'qa_events_submission_id_fkey'
            columns: ['submission_id']
            isOneToOne: false
            referencedRelation: 'submissions'
            referencedColumns: ['id']
          },
        ]
      }
      qa_jobs: {
        Row: {
          attempts: number
          completed_at: string | null
          last_error: string | null
          photo_id: string
          status: string
          updated_at: string
        }
        Insert: {
          attempts?: number
          completed_at?: string | null
          last_error?: string | null
          photo_id: string
          status?: string
          updated_at?: string
        }
        Update: {
          attempts?: number
          completed_at?: string | null
          last_error?: string | null
          photo_id?: string
          status?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: 'qa_jobs_photo_id_fkey'
            columns: ['photo_id']
            isOneToOne: true
            referencedRelation: 'photos'
            referencedColumns: ['id']
          },
        ]
      }
      service_state: {
        Row: {
          capture_open: boolean
          singleton: boolean
          updated_at: string
        }
        Insert: {
          capture_open?: boolean
          singleton?: boolean
          updated_at?: string
        }
        Update: {
          capture_open?: boolean
          singleton?: boolean
          updated_at?: string
        }
        Relationships: []
      }
      submissions: {
        Row: {
          collection_scope: 'legacy' | 'private_pilot'
          actor_id: string
          capture_method: string
          captured_at: string
          client_version: string | null
          contributor_id: string
          device_model: string | null
          disturbed: boolean | null
          elevation: number | null
          finalized_at: string | null
          geom_precise: unknown
          gps_accuracy_m: number | null
          grant_id: string
          h3_r6: string | null
          h3_r8: string | null
          id: string
          ingest_path: string
          is_synthetic: boolean
          land_cover: string | null
          location_source: string
          precip_flag: boolean | null
          provenance_tier: number
          status: string
          surface_condition: string | null
        }
        Insert: {
          collection_scope?: never
          // Set by the server (trigger) from the contributor; clients cannot write it.
          actor_id?: string
          capture_method?: string
          captured_at: string
          client_version?: string | null
          contributor_id: string
          device_model?: string | null
          disturbed?: boolean | null
          elevation?: number | null
          finalized_at?: string | null
          geom_precise: unknown
          gps_accuracy_m?: number | null
          grant_id: string
          h3_r6?: string | null
          h3_r8?: string | null
          id?: string
          ingest_path?: string
          is_synthetic?: boolean
          land_cover?: string | null
          location_source?: string
          precip_flag?: boolean | null
          provenance_tier?: number
          status?: string
          surface_condition?: string | null
        }
        Update: {
          collection_scope?: never
          actor_id?: string
          capture_method?: string
          captured_at?: string
          client_version?: string | null
          contributor_id?: string
          device_model?: string | null
          disturbed?: boolean | null
          elevation?: number | null
          finalized_at?: string | null
          geom_precise?: unknown
          gps_accuracy_m?: number | null
          grant_id?: string
          h3_r6?: string | null
          h3_r8?: string | null
          id?: string
          ingest_path?: string
          is_synthetic?: boolean
          land_cover?: string | null
          location_source?: string
          precip_flag?: boolean | null
          provenance_tier?: number
          status?: string
          surface_condition?: string | null
        }
        Relationships: [
          {
            foreignKeyName: 'submissions_actor_id_fkey'
            columns: ['actor_id']
            isOneToOne: false
            referencedRelation: 'actors'
            referencedColumns: ['id']
          },
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
      terms_versions: {
        Row: {
          published_at: string
          retired_at: string | null
          summary: string | null
          url: string | null
          version: string
        }
        Insert: {
          published_at: string
          retired_at?: string | null
          summary?: string | null
          url?: string | null
          version: string
        }
        Update: {
          published_at?: string
          retired_at?: string | null
          summary?: string | null
          url?: string | null
          version?: string
        }
        Relationships: []
      }
      upstream_buckets: {
        Row: {
          capacity: number
          refill_per_minute: number
          refilled_at: string
          source: string
          tokens: number
        }
        Insert: {
          capacity: number
          refill_per_minute: number
          refilled_at?: string
          source: string
          tokens: number
        }
        Update: {
          capacity?: number
          refill_per_minute?: number
          refilled_at?: string
          source?: string
          tokens?: number
        }
        Relationships: []
      }
    }
    Views: {
      attribution_review_queue: {
        Row: {
          attribution_name: string | null
          contributor_id: string | null
          first_accepted_at: string | null
          grants: number | null
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
    }
    Functions: {
      authorize_photo_privacy_export: {
        Args: { p_request: Json }
        Returns: Json
      }
      claim_photo_privacy_job: { Args: never; Returns: Json }
      complete_photo_privacy_job: {
        Args: { p_lease_id: string; p_receipt: Json }
        Returns: Json
      }
      fail_photo_privacy_job: {
        Args: { p_lease_id: string; p_error_code: string }
        Returns: Json
      }
      photo_privacy_capabilities: { Args: never; Returns: Json }
      photo_privacy_receipt: { Args: { p_photo_id: string }; Returns: Json }
      photo_privacy_review_context: {
        Args: { p_photo_id: string; p_operator_token: string }
        Returns: Json
      }
      record_photo_privacy_content: { Args: { p_request: Json }; Returns: Json }
      review_photo_privacy: {
        Args: { p_operator_token: string; p_request: Json }
        Returns: Json
      }
      apply_deletion_request: {
        Args: { p_request_id: string }
        Returns: {
          deleted_submissions: number
          withdrawn_grants: number
        }[]
      }
      auth_user_exists: { Args: { p_uid: string }; Returns: boolean }
      begin_prior_attempt: {
        Args: {
          p_costs: Json
          p_owner_request: boolean
          p_submission_id: string
        }
        Returns: {
          attempts: number | null
          outcome: string
          retry_after_seconds: number | null
        }[]
      }
      capture_is_open: { Args: never; Returns: boolean }
      claim_deletion_request: {
        Args: { p_stale?: unknown }
        Returns: {
          attempts: number
          auth_uid: string | null
          contributor_id: string
          kind: string
          request_id: string
        }[]
      }
      complete_deletion_request: {
        Args: { p_request_id: string }
        Returns: undefined
      }
      contributor_orphaned_objects: {
        Args: { p_auth_uid: string; p_limit?: number }
        Returns: {
          bucket_id: string
          name: string
        }[]
      }
      current_auth_user_exists: { Args: never; Returns: boolean }
      current_contributor_id: { Args: never; Returns: string }
      fail_prior_job: {
        Args: { p_reason: string; p_submission_id: string }
        Returns: undefined
      }
      finalize_submission: {
        Args: { p_submission_id: string }
        Returns: string
      }
      collection_pilot_capabilities: { Args: never; Returns: Json }
      collection_publication_capabilities: { Args: never; Returns: Json }
      library_intake_capabilities: { Args: never; Returns: Json }
      my_library_intake_receipt: {
        Args: { p_intake_id: string }
        Returns: Json
      }
      record_library_intake: { Args: { p_request: Json }; Returns: Json }
      set_library_intake_open: { Args: { p_open: boolean }; Returns: undefined }
      my_submission_accepts_uploads: {
        Args: { p_submission: string }
        Returns: boolean
      }
      orphaned_photo_objects: {
        Args: { p_limit?: number }
        Returns: {
          name: string
        }[]
      }
      refresh_public_h3_cells: { Args: { payload: Json }; Returns: number }
      release_deletion_request: {
        Args: {
          p_error: string
          p_request_id: string
          p_retry_after?: unknown
        }
        Returns: undefined
      }
      requeue_stale_prior_jobs: {
        Args: { p_older_than?: unknown }
        Returns: number
      }
      settle_submission: {
        Args: { p_submission_id: string }
        Returns: string
      }
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
