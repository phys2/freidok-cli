# Publications
{% for year, items in publications|groupby("publication_year.value")|reverse %}
   {# This shows how an authors list could be assembled within the template:  
       {% set comma = joiner(", ") %}
       {% set authors %} 
       {%- for author in pub.persons -%}
         {{ comma() }}{{ author.forename }} {{ author.surname }}
       {%-  endfor -%}
       {% endset %}
       {{ authors  | wordwrap(break_long_words=false, break_on_hyphens=false, wrapstring='\n   ') }}
   #}

## {{ year }}

{% for pub in items %}
-  {{ pub._extras_authors | wordwrap(break_long_words=false, break_on_hyphens=false, wrapstring='\n   ') }}

   {% if pub.titles %}
   {{ pub.titles[0].value | wordwrap(break_long_words=false, break_on_hyphens=false, wrapstring='\n   ') }}
   {% endif %}
   {% set source = pub.source_journal[0] %}
   {% if source %}

   {{ source.title }} 
   {%- if source.volume %} {{ source.volume }} {% endif %}
   {%- if source.year %}({{ source.year }}) {% endif %}
   {%- if source.issue %}{{ source.issue }}, {% endif %}
   {%- if source.page %}{{ source.page }}{% endif %}  
   {% endif %}
   {% if pub.pub_ids %}
   {{ pub.pub_ids[0].link }}
   {% endif %}

{% endfor %}
{% endfor %}
