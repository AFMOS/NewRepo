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

# Month order for sorting
month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Define quarter mapping
quarter_map = {
    'Q1': ["Jan", "Feb", "Mar"],
    'Q2': ["Apr", "May", "Jun"],
    'Q3': ["Jul", "Aug", "Sep"],
    'Q4': ["Oct", "Nov", "Dec"]
}

def apply_master_filter(df, search_term):
    if not search_term:
        return df

    search_term = search_term.lower()
    mask = pd.Series([False] * len(df))
    
    for col in ['customer_code', 'customer_name', 'customer_category', 'salesman', 
                'item_code', 'item_description', 'item_category', 'month', 'area']:
        if col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(search_term, regex=True)
    
    return df[mask]

def update_dashboard(selected_areas, selected_month, selected_quarter, 
                      selected_customer_categories, selected_salesmen, selected_item_categories,
                      selected_customer_names, selected_item_description, main_variable, search_term):
    # Apply master filter
    filtered_data = apply_master_filter(data, search_term)
    
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
    total_sales = filtered_data[main_variable].sum()  # Calculate based on filtered data
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

    # Sales by Month Bar Chart
    sales_by_month = filtered_data.groupby('month')[main_variable].sum().reset_index()
    sales_by_month['month'] = pd.Categorical(sales_by_month['month'], categories=month_order, ordered=True)
    sales_by_month = sales_by_month.sort_values('month')

    # Calculate percentage change
    sales_by_month['Change %'] = sales_by_month[main_variable].pct_change() * 100
    sales_by_month['Change %'] = sales_by_month['Change %'].fillna(0).round(1).astype(str) + '%'

    # Round sales values
    sales_by_month[main_variable] = sales_by_month[main_variable].round(0)

    fig_month = px.bar(sales_by_month, y='month', x=main_variable, title='Sales by Month', text=main_variable, orientation='h')
    fig_month.update_traces(
        texttemplate='%{text:.0s}<br>%{customdata}', 
        customdata=sales_by_month['Change %'],  # Adding percentage change
        textposition='inside', 
        textangle=0  # Horizontal text alignment
    )
    fig_month.update_layout(
        xaxis_title='',
        yaxis_title='',
        title='Sales by Month'
    )

    # Sales by Quarter Bar Chart with Percentage Change
    sales_by_quarter = filtered_data.copy()
    sales_by_quarter['quarter'] = sales_by_quarter['month'].apply(lambda x: next((q for q, months in quarter_map.items() if x in months), None))
    sales_by_quarter = sales_by_quarter.groupby('quarter')[main_variable].sum().reset_index()
    
    # Calculate percentage change
    sales_by_quarter = sales_by_quarter.sort_values('quarter')
    sales_by_quarter['Change %'] = sales_by_quarter[main_variable].pct_change() * 100
    sales_by_quarter['Change %'] = sales_by_quarter['Change %'].fillna(0).round(1).astype(str) + '%'
    
    fig_quarter = px.bar(sales_by_quarter, x='quarter', y=main_variable, title='Sales by Quarter', text=main_variable)
    
    # Update text to include percentage change without "Change" label
    fig_quarter.update_traces(
        texttemplate='%{text:.0s}<br>%{customdata}',
        customdata=sales_by_quarter['Change %'],
        textposition='inside'
    )
    
    fig_quarter.update_layout(
        xaxis_title='',
        yaxis_title='',
        title='Sales by Quarter'
    )
    
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
    
    fig_salesman.update_traces(texttemplate='%{text:.0s}', textposition='inside')  # Updated format to match weight
    fig_salesman.update_layout(
        xaxis_title='',
        yaxis_title='',
        xaxis=dict(tickangle=-45),  # Rotate x-axis labels for readability
        legend_title='Area',  # Title for the legend
        barmode='stack'  # Stack the bars
    )
    
    # Generate Item Category Heatmap
    pivot_table_item = filtered_data.pivot_table(index='item_category', columns='month', values=main_variable, aggfunc='sum')
    
    # Ensure columns are sorted by month order
    pivot_table_item = pivot_table_item.reindex(columns=month_order)
    
    # Sort rows by total value in descending order
    pivot_table_item['total'] = pivot_table_item.sum(axis=1)
    pivot_table_item = pivot_table_item.sort_values('total', ascending=True)
    pivot_table_item = pivot_table_item.drop('total', axis=1)
    
    # Round the values and replace NaN with empty string
    rounded_values_item = pivot_table_item.round(0).fillna('') 
    text_values_item = rounded_values_item.astype(str)
    text_values_item = text_values_item.replace('0.0', '', regex=False)
    
    # Create heatmap for Item Category using go.Heatmap
    fig_heatmap_item = go.Figure(data=go.Heatmap(
        z=pivot_table_item.values,
        x=pivot_table_item.columns,
        y=pivot_table_item.index,
        colorscale='Brwnyl',  # New color scale
        hoverongaps=False,
        text=text_values_item,
        texttemplate="%{text}",
        showscale=False  # Hide the color scale (legend)
    ))
    
    fig_heatmap_item.update_layout(
        title='',
        xaxis_title='',
        yaxis_title='',
        height=25 * len(pivot_table_item.index),  # Adjust height based on number of rows and desired row height
        xaxis=dict(side='top')  # Move x-axis labels to the top
    )

    # Generate new Item Description Heatmap
    pivot_table_item_description = filtered_data.pivot_table(index='item_description', columns='month', values=main_variable, aggfunc='sum')
    
    # Ensure columns are sorted by month order
    pivot_table_item_description = pivot_table_item_description.reindex(columns=month_order)
    
    # Sort rows by total value in descending order
    pivot_table_item_description['total'] = pivot_table_item_description.sum(axis=1)
    pivot_table_item_description = pivot_table_item_description.sort_values('total', ascending=True)
    pivot_table_item_description = pivot_table_item_description.drop('total', axis=1)
    
    # Round the values and replace NaN with empty string
    rounded_values_item_description = pivot_table_item_description.round(0).fillna('')
    text_values_item_description = rounded_values_item_description.astype(str)
    text_values_item_description = text_values_item_description.replace('0.0', '', regex=False)
    
    # Create heatmap for Item Description using go.Heatmap
    fig_heatmap_item_description = go.Figure(data=go.Heatmap(
        z=pivot_table_item_description.values,
        x=pivot_table_item_description.columns,
        y=pivot_table_item_description.index,
        colorscale='Brwnyl',  # New color scale
        hoverongaps=False,
        text=text_values_item_description,
        texttemplate="%{text}",
        showscale=False  # Hide the color scale (legend)
    ))
    
    fig_heatmap_item_description.update_layout(
        title='',
        xaxis_title='',
        yaxis_title='',
        height=20 * len(pivot_table_item_description.index),  # Adjust height based on number of rows and desired row height
        xaxis=dict(side='top')  # Move x-axis labels to the top
    )

    # Generate Customer Heatmap
    pivot_table_customer = filtered_data.pivot_table(index='customer_name', columns='month', values=main_variable, aggfunc='sum')
    
    # Ensure columns are sorted by month order
    pivot_table_customer = pivot_table_customer.reindex(columns=month_order)
    
    # Sort rows by total value in descending order
    pivot_table_customer['total'] = pivot_table_customer.sum(axis=1)
    pivot_table_customer = pivot_table_customer.sort_values('total', ascending=True)
    pivot_table_customer = pivot_table_customer.drop('total', axis=1)
    
    # Round the values and replace NaN with empty string
    rounded_values_customer = pivot_table_customer.round(0).fillna('')
    text_values_customer = rounded_values_customer.astype(str)
    text_values_customer = text_values_customer.replace('0.0', '', regex=False)
    
    # Create heatmap for Customer using go.Heatmap
    fig_heatmap_customer = go.Figure(data=go.Heatmap(
        z=pivot_table_customer.values,
        x=pivot_table_customer.columns,
        y=pivot_table_customer.index,
        colorscale='Brwnyl',  # New color scale
        hoverongaps=False,
        text=text_values_customer,
        texttemplate="%{text}",
        showscale=False  # Hide the color scale (legend)
    ))
    
    fig_heatmap_customer.update_layout(
        title='',
        xaxis_title='',
        yaxis_title='',
        height=20 * len(pivot_table_customer.index),  # Adjust height based on number of rows and desired row height
        xaxis=dict(side='top')  # Move x-axis labels to the top
    )

    return (total_sales, customer_count, total_weight, Cash_count, Credit_count,
            Cash_percentage, Credit_percentage, fig_area, fig_month, fig_quarter, fig_salesman, 
            fig_heatmap_item, fig_heatmap_item_description, fig_heatmap_customer)

# Streamlit app
st.markdown("""<h1 style="text-align: center;">📊 Sales Dashboard</h1>""", unsafe_allow_html=True)

# Filters aligned to the right
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

# Update dashboard based on selections
(total_sales, customer_count, total_weight, Cash_count, Credit_count,
 Cash_percentage, Credit_percentage, fig_area, fig_month, fig_quarter, fig_salesman, 
 fig_heatmap_item, fig_heatmap_item_description, fig_heatmap_customer) = update_dashboard(
    selected_areas, selected_month, selected_quarter, 
    selected_customer_categories, selected_salesmen, selected_item_categories,
    selected_customer_names, selected_item_description,
    main_variable, search_term
)

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

# Display charts side by side and centered
st.subheader('')
col1, col2, col3, col4 = st.columns([3, 3, 3, 3])  # Adjust column widths to be equal

with col1:
    st.plotly_chart(fig_area, use_container_width=True)

with col2:
    st.plotly_chart(fig_month, use_container_width=True)

with col3:
    st.plotly_chart(fig_quarter, use_container_width=True)

with col4:
    st.plotly_chart(fig_salesman, use_container_width=True)

# Add expand/collapse sections for heatmaps
with st.expander("Item Category Heatmap", expanded=False):
    st.plotly_chart(fig_heatmap_item, use_container_width=True)

with st.expander("Item Description Heatmap", expanded=False):
    st.plotly_chart(fig_heatmap_item_description, use_container_width=True)

with st.expander("Customer Heatmap", expanded=False):
    st.plotly_chart(fig_heatmap_customer, use_container_width=True)
