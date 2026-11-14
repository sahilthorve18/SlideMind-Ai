import React from 'react'
import {
  CompetitorMatrix2x2,
  MarketAdoptionGaussian,
  ChevronFunnel,
  MilestoneRoadmap,
} from './StrategicLayouts'
import {
  PhotoMosaic2x2,
  PhotoMosaic3Col,
  WaveEditorialLayout,
  AgendaGrid9Box,
  RadialHubSpoke,
  SplitScreenMedia,
  TeamGridAvatars,
} from './EditorialLayouts'
import {
  StatsKpiMonument,
  StatsKpiTriple,
  MarketOpportunityRadial,
  FinancialTableMatrix,
} from './MetricLayouts'
import {
  TechnicalArchitectureFlow,
  ComparisonTable,
  HorizontalProcess4Step,
  SwotAnalysisMatrix,
} from './TechnicalLayouts'
import {
  TicketLifecycleFlow,
  FeatureShowcase,
  OperationalDashboard,
} from './OperationalLayouts'

/**
 * LayoutDispatcher.jsx
 * Central routing engine that renders 50+ structurally diverse slide compositions.
 * Matches layout key to specialized React components, passing verified theme tokens.
 */
export function renderAdvancedLayout(layout, { slide, content, title, theme, bullets }) {
  const normLayout = (layout || '').toLowerCase().trim()

  // Strategic & Analysis
  if (normLayout === 'competitor_matrix_2x2' || normLayout === 'competitor_analysis' || normLayout === 'competitor_advantages_grid') {
    return <CompetitorMatrix2x2 content={content} title={title} theme={theme} />
  }
  if (normLayout === 'market_adoption_gaussian' || normLayout === 'market_adoption' || normLayout === 'bell_curve') {
    return <MarketAdoptionGaussian content={content} title={title} theme={theme} />
  }
  if (normLayout === 'chevron_funnel' || normLayout === 'customer_acquisition' || normLayout === 'acquisition_funnel') {
    return <ChevronFunnel content={content} title={title} theme={theme} />
  }
  if (normLayout === 'milestone_roadmap' || normLayout === 'milestones' || normLayout === 'vertical_timeline_milestones') {
    return <MilestoneRoadmap content={content} title={title} theme={theme} />
  }
  if (normLayout === 'swot_analysis_matrix') {
    return <SwotAnalysisMatrix content={content} title={title} theme={theme} />
  }

  // Editorial & Media
  if (normLayout === 'photo_mosaic_2x2' || normLayout === 'image_mosaic') {
    return <PhotoMosaic2x2 content={content} title={title} theme={theme} />
  }
  if (normLayout === 'photo_mosaic_3col' || normLayout === 'magazine_article_columns') {
    return <PhotoMosaic3Col content={content} title={title} theme={theme} />
  }
  if (normLayout === 'wave_editorial_cover' || normLayout === 'customer_profile' || normLayout === 'the_competition') {
    return <WaveEditorialLayout content={content} title={title} theme={theme} />
  }
  if (normLayout === 'agenda_grid_9box' || normLayout === 'our_agenda' || normLayout === 'table_of_contents') {
    return <AgendaGrid9Box content={content} title={title} theme={theme} />
  }
  if (normLayout === 'radial_hub_spoke' || normLayout === 'circular_lifecycle_diagram') {
    return <RadialHubSpoke content={content} title={title} theme={theme} />
  }
  if (normLayout === 'split_screen_media' || normLayout === 'split_hero') {
    return <SplitScreenMedia content={content} title={title} theme={theme} />
  }
  if (normLayout === 'team_grid_avatars' || normLayout === 'the_team') {
    return <TeamGridAvatars content={content} title={title} theme={theme} />
  }

  // Data & KPI
  if (normLayout === 'stats_kpi_monument') {
    return <StatsKpiMonument content={content} title={title} theme={theme} />
  }
  if (normLayout === 'stats_kpi_triple' || normLayout === 'kpi_bento_grid') {
    return <StatsKpiTriple content={content} title={title} theme={theme} />
  }
  if (normLayout === 'market_opportunity_radial' || normLayout === 'donut_market_share') {
    return <MarketOpportunityRadial content={content} title={title} theme={theme} />
  }
  if (normLayout === 'financial_table_matrix' || normLayout === 'unit_economics_breakdown') {
    return <FinancialTableMatrix content={content} title={title} theme={theme} />
  }

  // Technical & Comparison
  if (normLayout === 'technical_architecture_flow' || normLayout === 'architecture_diagram') {
    return <TechnicalArchitectureFlow content={content} title={title} theme={theme} />
  }
  if (normLayout === 'comparison_table' || normLayout === 'pros_cons_comparison') {
    return <ComparisonTable content={content} title={title} theme={theme} />
  }
  if (normLayout === 'horizontal_process_4step') {
    return <HorizontalProcess4Step content={content} title={title} theme={theme} />
  }

  // Operational & Workflows
  if (normLayout === 'ticket_lifecycle_flow' || normLayout === 'horizontal_process_workflow' || normLayout === 'process_workflow' || normLayout === 'process_diagram' || normLayout === 'timeline') {
    return <TicketLifecycleFlow content={content} title={title} theme={theme} />
  }
  if (normLayout === 'feature_showcase' || normLayout === 'operational_capabilities' || normLayout === 'digital_record_cards') {
    return <FeatureShowcase content={content} title={title} theme={theme} />
  }
  if (normLayout === 'kpi_dashboard' || normLayout === 'admin_monitoring_dashboard' || normLayout === 'operations_dashboard') {
    return <OperationalDashboard content={content} title={title} theme={theme} />
  }

  // If not handled by advanced components, return null to fall back to SlideView's native rendering
  return null
}
