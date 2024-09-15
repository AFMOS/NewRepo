import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import re

# Set the page configuration to wide mode
st.set_page_config(layout="wide")

# Main variable selector (removed "Qty")
main_variable_options = {"Total": "total", "Weight": "weight"}
main_variable = st.sidebar.radio(
    "Select Main Variable",
    options=list(main_variable_options.keys()),
    index=list(main_variable_options.keys()).index("Total")  # Set default index
)
main_variable = main_variable_options[main_variable]

# File uploader
uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])

# Load the data
if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file)
else:
    # Default data file
    try:
        data = pd.read_csv('sales_data.csv')  # Replace with the path to your CSV file
    except FileNotFoundError:
        st.error("The file 'sales_data.csv' was not found.")
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("The file 'sales_data.csv' is empty.")
        st.stop()
    except pd.errors.ParserError:
        st.error("Error parsing 'sales_data.csv'. Please check the file format.")
        st.stop()

# Define all possible months
all_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Get the months present in the data
present_months = sorted(data['month'].unique(), key=lambda x: all_months.index(x))

# Use only the months present in the data for month_order
month_order = present_months

# Define quarter mapping
quarter_map = {
    'Q1': ["Jan", "Feb", "Mar"],
    'Q2': ["Apr", "May", "Jun"],
    'Q3': ["Jul", "Aug", "Sep"],
    'Q4': ["Oct", "Nov", "Dec"]
}

def apply_master_filter(df, search_term):
    if not search_term:
        return df, True

    search_term = search_term.lower()
    mask = pd.Series([False] * len(df))
    
    for col in ['customer_code', 'customer_name', 'customer_category', 'salesman', 
                'item_code', 'item_description', 'item_category', 'month', 'area']:
        if col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(search_term, regex=True)
    
    filtered_df = df[mask]
    search_found = len(filtered_df) > 0
    return filtered_df, search_found

def generate_dashboard_title(search_term, selected_filters):
    title_parts = []
    
    if search_term:
        title_parts.append(f'<span style="color: maroon;">"{search_term}"</span>')
    
    for filter_name, filter_value in selected_filters.items():
        if filter_value and filter_value != "None":
            title_parts.append(f'<span style="color: maroon;">{filter_value}</span>')
    
    if title_parts:
        return f"{' - '.join(title_parts)} Breakdown"
    else:
        return "Sales Dashboard"

def update_dashboard(selected_areas, selected_month, selected_quarter, 
                      selected_customer_categories, selected_salesmen, selected_item_categories,
                      selected_customer_names, selected_item_description, main_variable, search_term):
    # Apply master filter
    filtered_data, search_found = apply_master_filter(data, search_term)
    
    if not search_found:
        return None, False  # Return None for the data and False for search_found
    
    # Further filtering based on other selections
    if selected_areas and selected_areas != "None":
        filtered_data = filtered_data[filtered_data['area'] == selected_areas]
    if selected_month and selected_month != "None":
        filtered_data = filtered_data[filtered_data['month'] == selected_month]
    if selected_quarter and selected_quarter != "None":
        months = quarter_map[selected_quarter]
        filtered_data = filtered_data[filtered_data['month'].isin(months)]
    if selected_customer_categories and selected_customer_categories != "None":
        filtered_data = filtered_data[filtered_data['customer_category'] == selected_customer_categories]
    if selected_salesmen and selected_salesmen != "None":
        filtered_data = filtered_data[filtered_data['salesman'] == selected_salesmen]
    if selected_item_categories and selected_item_categories != "None":
        filtered_data = filtered_data[filtered_data['item_category'] == selected_item_categories]
    if selected_customer_names and selected_customer_names != "None":
        filtered_data = filtered_data[filtered_data['customer_name'] == selected_customer_names]
    if selected_item_description and selected_item_description != "None":
        filtered_data = filtered_data[filtered_data['item_description'] == selected_item_description]

    # Calculate summary statistics
    total_sales = filtered_data[main_variable].sum()
    customer_count = filtered_data['customer_code'].nunique()
    total_weight = filtered_data['weight'].sum()
    
    total_customers = filtered_data['customer_code'].nunique()
    if total_customers > 0:
        Cash_count = filtered_data[filtered_data['payment_type'] == 'Cash']['customer_code'].nunique()
        Credit_count = filtered_data[filtered_data['payment_type'] == 'Credit']['customer_code'].nunique()
        
        Cash_percentage = Cash_count / total_customers
        Credit_percentage = Credit_count / total_customers
    else:
        Cash_count = Credit_count = 0
        Cash_percentage = Credit_percentage = 0

    # Create charts using Plotly
    # Sales by Area Pie Chart
    sales_by_area = filtered_data.groupby('area')[main_variable].sum().reset_index()
    fig_area = px.pie(sales_by_area, values=main_variable, names='area', title='Sales by Area')

    # Combined Time Graph (Monthly and Quarterly)
    sales_by_month = filtered_data.groupby('month')[main_variable].sum().reset_index()
    sales_by_month['month'] = pd.Categorical(sales_by_month['month'], categories=month_order, ordered=True)
    sales_by_month = sales_by_month.sort_values('month')
    
    sales_by_quarter = filtered_data.copy()
    sales_by_quarter['quarter'] = sales_by_quarter['month'].apply(lambda x: next((q for q, months in quarter_map.items() if x in months), None))
    sales_by_quarter = sales_by_quarter.groupby('quarter')[main_variable].sum().reset_index()
    
    fig_time = go.Figure()

    # Add monthly data as bars
    fig_time.add_trace(go.Bar(
        x=sales_by_month['month'],
        y=sales_by_month[main_variable],
        name='Monthly Sales',
        marker_color='rgba(55, 83, 109, 0.7)',
        text=sales_by_month[main_variable].apply(lambda x: f'{x:,.0f}'),
        textposition='inside',
        textfont=dict(color='white'),
    ))

    # Calculate and add percentage change for monthly data
    sales_by_month['pct_change'] = sales_by_month[main_variable].pct_change() * 100
    for i, row in sales_by_month.iterrows():
        fig_time.add_annotation(
            x=row['month'],
            y=row[main_variable],
            text=f"{row['pct_change']:.1f}%" if not pd.isna(row['pct_change']) else "",
            showarrow=False,
            yshift=20,
            font=dict(size=10, color='rgba(55, 83, 109, 1)')
        )

    # Add quarterly data as lines with markers
    quarter_positions = {'Q1': 1, 'Q2': 4, 'Q3': 7, 'Q4': 10}
    fig_time.add_trace(go.Scatter(
        x=[month_order[quarter_positions[q]-1] for q in sales_by_quarter['quarter']],
        y=sales_by_quarter[main_variable],
        mode='lines+markers+text',
        name='Quarterly Sales',
        line=dict(color='rgba(255, 0, 0, 0.8)', width=3),
        marker=dict(size=12, symbol='star', color='rgba(255, 0, 0, 0.8)'),
        text=sales_by_quarter[main_variable].apply(lambda x: f'{x:,.0f}'),
        textposition='top center',
        textfont=dict(color='rgba(255, 0, 0, 1)'),
    ))

    # Calculate and add percentage change for quarterly data
    sales_by_quarter['pct_change'] = sales_by_quarter[main_variable].pct_change() * 100
    for i, row in sales_by_quarter.iterrows():
        fig_time.add_annotation(
            x=month_order[quarter_positions[row['quarter']]-1],
            y=row[main_variable],
            text=f"{row['pct_change']:.1f}%" if not pd.isna(row['pct_change']) else "",
            showarrow=False,
            yshift=30,
            font=dict(size=10, color='rgba(255, 0, 0, 0.8)')
        )

    # Update layout
    fig_time.update_layout(
        title='Monthly and Quarterly Sales',
        xaxis_title='Month',
        yaxis_title=f'Sales ({main_variable.capitalize()})',
        legend_title='Period',
        hovermode="x unified",
        barmode='overlay',
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(l=50, r=50, t=80, b=50),
    )

    fig_time.update_xaxes(tickangle=-45)
    
    # Sales by Salesman and Area Stacked Bar Chart
    sales_by_salesman_area = filtered_data.groupby(['salesman', 'area'])[main_variable].sum().reset_index()
    
    # Sort salesmen by total sales
    salesman_order = sales_by_salesman_area.groupby('salesman')[main_variable].sum().sort_values(ascending=False).index
    
    # Create the stacked bar chart
    fig_salesman = px.bar(sales_by_salesman_area, 
                          x='salesman', 
                          y=main_variable, 
                          color='area',
                          title='Sales by Salesman and Area',
                          labels={main_variable: 'Total Sales', 'salesman': 'Salesman', 'area': 'Area'},
                          category_orders={'salesman': salesman_order},
                          text=main_variable)
    
    fig_salesman.update_traces(texttemplate='%{text:.0s}', textposition='inside')
    fig_salesman.update_layout(
        xaxis_title='',
        yaxis_title='',
        xaxis=dict(tickangle=-45),
        legend_title='Area',
        barmode='stack'
    )
    
    # Generate Item Category Heatmap
    pivot_table_item = filtered_data.pivot_table(index='item_category', columns='month', values=main_variable, aggfunc='sum')
    pivot_table_item = pivot_table_item.reindex(columns=month_order)
    pivot_table_item['total'] = pivot_table_item.sum(axis=1)
    pivot_table_item = pivot_table_item.sort_values('total', ascending=True)
    pivot_table_item = pivot_table_item.drop('total', axis=1)
    
    rounded_values_item = pivot_table_item.round(0).fillna('') 
    text_values_item = rounded_values_item.astype(str)
    text_values_item = text_values_item.replace('0.0', '', regex=False)
    
    fig_heatmap_item = go.Figure(data=go.Heatmap(
        z=pivot_table_item.values,
        x=pivot_table_item.columns,
        y=pivot_table_item.index,
        colorscale='Brwnyl',
        hoverongaps=False,
        text=text_values_item,
        texttemplate="%{text}",
        showscale=False
    ))
    
    fig_heatmap_item.update_layout(
        title='',
        xaxis_title='',
        yaxis_title='',
        height=25 * len(pivot_table_item.index),
        xaxis=dict(side='top')
    )

    # Generate Item Description Heatmap
    pivot_table_item_description = filtered_data.pivot_table(index='item_description', columns='month', values=main_variable, aggfunc='sum')
    pivot_table_item_description = pivot_table_item_description.reindex(columns=month_order)
    pivot_table_item_description['total'] = pivot_table_item_description.sum(axis=1)
    pivot_table_item_description = pivot_table_item_description.sort_values('total', ascending=True)
    pivot_table_item_description = pivot_table_item_description.drop('total', axis=1)
    
    rounded_values_item_description = pivot_table_item_description.round(0).fillna('')
    text_values_item_description = rounded_values_item_description.astype(str)
    text_values_item_description = text_values_item_description.replace('0.0', '', regex=False)
    
    fig_heatmap_item_description = go.Figure(data=go.Heatmap(
        z=pivot_table_item_description.values,
        x=pivot_table_item_description.columns,
        y=pivot_table_item_description.index,
        colorscale='Brwnyl',
        hoverongaps=False,
        text=text_values_item_description,
        texttemplate="%{text}",
        showscale=False
    ))
    
    fig_heatmap_item_description.update_layout(
        title='',
        xaxis_title='',
        yaxis_title='',
        height=20 * len(pivot_table_item_description.index),
        xaxis=dict(side='top')
    )

    # Generate Customer Heatmap
    pivot_table_customer = filtered_data.pivot_table(index='customer_name', columns='month', values=main_variable, aggfunc='sum')
    pivot_table_customer = pivot_table_customer.reindex(columns=month_order)
    pivot_table_customer['total'] = pivot_table_customer.sum(axis=1)
    pivot_table_customer = pivot_table_customer.sort_values('total', ascending=True)
    pivot_table_customer = pivot_table_customer.drop('total', axis=1)
    
    rounded_values_customer = pivot_table_customer.round(0).fillna('')
    text_values_customer = rounded_values_customer.astype(str)
    text_values_customer = text_values_customer.replace('0.0', '', regex=False)
    
    fig_heatmap_customer = go.Figure(data=go.Heatmap(
        z=pivot_table_customer.values,
        x=pivot_table_customer.columns,
        y=pivot_table_customer.index,
        colorscale='Brwnyl',
        hoverongaps=False,
        text=text_values_customer,
        texttemplate="%{text}",
        showscale=False
    ))
    
    fig_heatmap_customer.update_layout(
        title='',
        xaxis_title='',
        yaxis_title='',
        height=20 * len(pivot_table_customer.index),
        xaxis=dict(side='top')
    )

    # Calculate monthly KPIs for Salesman tab
    monthly_kpis = filtered_data.groupby('month').agg({
        main_variable: 'sum',
        'customer_code': 'nunique',
        'item_category': 'nunique'
    }).reset_index()
    
    # Sort the data by month order
    monthly_kpis['month'] = pd.Categorical(monthly_kpis['month'], categories=month_order, ordered=True)
    monthly_kpis = monthly_kpis.sort_values('month')
    
    # Calculate new customers
    all_customers = set()
    new_customers = []
    for i, (_, row) in enumerate(monthly_kpis.iterrows()):
        if i == 0:  # First month (January)
            new_customers.append(0)
            all_customers.update(filtered_data[filtered_data['month'] == row['month']]['customer_code'])
        else:
            month_customers = set(filtered_data[filtered_data['month'] == row['month']]['customer_code'])
            new_month_customers = month_customers - all_customers
            new_customers.append(len(new_month_customers))
            all_customers.update(month_customers)
    
    monthly_kpis['New Customer'] = new_customers

   # Calculate Newly Listed (new approach)
    newly_listed = []
    total_newly_listed = 0
    all_combinations = set()

    for month in month_order:
        month_data = filtered_data[filtered_data['month'] == month]
        
        # Get unique item-customer combinations for this month
        month_combinations = set(zip(month_data['customer_code'], month_data['item_code']))
        
        # Count new combinations
        new_combinations = month_combinations - all_combinations
        month_newly_listed = len(new_combinations)
        
        newly_listed.append(month_newly_listed)
        total_newly_listed += month_newly_listed
        
        # Update all combinations
        all_combinations.update(month_combinations)
    
    monthly_kpis['Newly Listed'] = newly_listed

    # Print total newly listed for verification
    print(f"Total Newly Listed: {total_newly_listed}")

    # Print additional information for debugging
    print(f"Total rows in filtered_data: {len(filtered_data)}")
    print(f"Number of unique customers: {filtered_data['customer_code'].nunique()}")
    print(f"Number of unique item codes: {filtered_data['item_code'].nunique()}")
    print(f"Number of unique customer-item combinations: {len(all_combinations)}")
    print(f"Months present in data: {month_order}")
    
    # Calculate additional KPIs
    monthly_kpis['change%'] = monthly_kpis[main_variable].pct_change() * 100
    monthly_kpis['progress%'] = (monthly_kpis[main_variable].cumsum() / monthly_kpis[main_variable].sum()) * 100
    monthly_kpis['customers%'] = (monthly_kpis['customer_code'] / filtered_data['customer_code'].nunique()) * 100
    monthly_kpis['%CTG. Consumption'] = (monthly_kpis['item_category'] / filtered_data['item_category'].nunique()) * 100
    
    # Create a DataFrame for display
    display_df = pd.DataFrame({
        'Month': monthly_kpis['month'],
        'Sales': monthly_kpis[main_variable],
        'New Customers': monthly_kpis['New Customer'],
        'Newly Listed': monthly_kpis['Newly Listed'],
        'Change%': monthly_kpis['change%'],
        'Progress%': monthly_kpis['progress%'],
        'Customers%': monthly_kpis['customers%'],
        '%CTG. Consumption': monthly_kpis['item_category'] / filtered_data['item_category'].nunique() * 100
    })
    
    #Set Month as index for better display
    display_df.set_index('Month', inplace=True)

    return (total_sales, customer_count, total_weight, Cash_count, Credit_count,
            Cash_percentage, Credit_percentage, fig_area, fig_time, fig_salesman, 
            fig_heatmap_item, fig_heatmap_item_description, fig_heatmap_customer, display_df), True

# Streamlit app
st.sidebar.header('Filters')

# Add master search filter
search_term = st.sidebar.text_input("Master Search Filter")

selected_areas = st.sidebar.selectbox('Select Area', options=['None'] + list(data['area'].unique()))
selected_month = st.sidebar.selectbox('Select Month', options=['None'] + list(data['month'].unique()))
selected_quarter = st.sidebar.selectbox('Select Quarter', options=['None'] + list(quarter_map.keys()))
selected_customer_categories = st.sidebar.selectbox('Select Customer Category', options=['None'] + list(data['customer_category'].unique()))
selected_salesmen = st.sidebar.selectbox('Select Salesman', options=['None'] + list(data['salesman'].unique()))
selected_item_categories = st.sidebar.selectbox('Select Item Category', options=['None'] + list(data['item_category'].unique()))
selected_customer_names = st.sidebar.selectbox('Select Customer Name', options=['None'] + list(data['customer_name'].unique()))
selected_item_description = st.sidebar.selectbox('Select Item Description', options=['None'] + list(data['item_description'].unique()))

# Generate dynamic dashboard title
selected_filters = {
    'Area': selected_areas,
    'Month': selected_month,
    'Quarter': selected_quarter,
    'Customer Category': selected_customer_categories,
    'Salesman': selected_salesmen,
    'Item Category': selected_item_categories,
    'Customer Name': selected_customer_names,
    'Item Description': selected_item_description
}
dashboard_title = generate_dashboard_title(search_term, selected_filters)

# Display the dynamic dashboard title
st.markdown(f"""<h1 style="text-align: center;">📊 {dashboard_title}</h1>""", unsafe_allow_html=True)

# Update dashboard based on selections
dashboard_data, search_found = update_dashboard(
    selected_areas, selected_month, selected_quarter, 
    selected_customer_categories, selected_salesmen, selected_item_categories,
    selected_customer_names, selected_item_description,
    main_variable, search_term
)

if not search_found:
    st.error("Search Not Found!")
else:
    (total_sales, customer_count, total_weight, Cash_count, Credit_count,
     Cash_percentage, Credit_percentage, fig_area, fig_time, fig_salesman, 
     fig_heatmap_item, fig_heatmap_item_description, fig_heatmap_customer, display_df) = dashboard_data

    # Layout with columns for summary statistics
    col1, col2, col3 = st.columns(3)  # Adjust to have 3 equal-width columns

    with col1:
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
            <h4 style="margin: 0; font-size: 14px;">Total</h4>
            <h2 style="margin: 0; font-size: 16px;">
            {'SAR' if main_variable == 'total' else 'Kg'} {total_sales:,.0f}
            </h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
            <h4 style="margin: 0; font-size: 14px;">Customer Count</h4>
            <h2 style="margin: 0; font-size: 16px;">{customer_count:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
            <h4 style="margin: 0; font-size: 14px;">Payment Type</h4>
            <h2 style="margin: 0; font-size: 16px;">Cash: {Cash_count:,} ({Cash_percentage:.1%})</h2>
            <h2 style="margin: 0; font-size: 16px;">Credit: {Credit_count:,} ({Credit_percentage:.1%})</h2>
        </div>
        """, unsafe_allow_html=True)

    # Create tabs for charts
    tab1, tab2, tab3, tab4 = st.tabs(["Sales Overview", "Time Graphs", "Heatmaps", "Salesman"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_area, use_container_width=True)
        with col2:
            st.plotly_chart(fig_salesman, use_container_width=True)

    with tab2:
        st.plotly_chart(fig_time, use_container_width=True)

    with tab3:
        heatmap_option = st.selectbox(
            "Select Heatmap",
            ["Item Category", "Item Description", "Customer"]
        )
        
        if heatmap_option == "Item Category":
            st.plotly_chart(fig_heatmap_item, use_container_width=True)
        elif heatmap_option == "Item Description":
            st.plotly_chart(fig_heatmap_item_description, use_container_width=True)
        else:  # Customer
            st.plotly_chart(fig_heatmap_customer, use_container_width=True)

    with tab4:
        # Display the table
        st.write("Monthly KPIs")
        
        # Use an expander to show/hide the full table
        with st.expander("Full Table", expanded=False):
            st.dataframe(display_df.style.format({
                'Sales': '{:,.0f}',
                'New Customers': '{:,.0f}',
                'Newly Listed': '{:.0f}',
                'Change%': '{:+.2f}%',
                'Progress%': '{:.2f}%',
                'Customers%': '{:.2f}%',
                '%CTG. Consumption': '{:.2f}%'
            }))
        
        
