# Institutions

{% for inst in items %}
{% if inst.link %}
## [{{ inst.id }}]({{ inst.link }})
{% else %}
## {{ inst.id }}
{% endif %}

{% for name in inst.names %}
  -  {{ name.value }}
{% endfor %}

{% endfor %}
